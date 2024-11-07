import time
import numpy as np
import os, sys, shutil
from contextlib import contextmanager
from numba import cuda as ncuda
import PIL
from PIL import Image, ImageFilter, ImageDraw, ImageFont
import cv2
import contextlib
from copy import deepcopy
import subprocess
from glob import glob
from os import path as osp
from os import path
	
utilspath = os.path.join(os.getcwd(), 'utils/')

@contextmanager
def timing(description: str) -> None:
  
	start = time.time()
	
	yield
	elapsed_time = time.time() - start

	print( description + ': finished in ' + f"{elapsed_time:.4f}" + ' s' )


class Quiet:
	
	def __init__(self):
		
		#Store initial stdout in this variable
		self._stdout = sys.stdout
		
	def __del__(self):
		
		sys.stdout = self._stdout

	@contextmanager
	def suppress_stdout(self, raising = False):

		with open(os.devnull, "w") as devnull:
			error_raised = False
			error = "there was an error"
			sys.stdout = devnull
			try:  
				yield
			except Exception as e:
				error_raised = True  
				error = e
				sys.stdout = self._stdout
				print(e)
			finally:
				finished = True
				sys.stdout = self._stdout

		sys.stdout = self._stdout		 
		if error_raised:
			if raising:
				raise(error)
			else:
				print(error)


	#Mute stdout inside this context
	@contextmanager
	def quiet_and_timeit(self, description = "Process running", raising = False, quiet = True):

		print(description+"...", end = '')
		start = time.time()
		try:

			if quiet:
				#with suppress_stdout(raising):	
				sys.stdout = open(os.devnull, "w")
			yield
			if quiet:
				sys.stdout = self._stdout
		except Exception as e:
			if quiet:
				sys.stdout = self._stdout
			if raising:
				sys.stdout = self._stdout
				raise(e)
			else:
				sys.stdout = self._stdout
				print(e)

		elapsed_time = time.time() - start
		
		sys.stdout = self._stdout
		print(': finished in ' + f"{elapsed_time:.4f}" + ' s' )
		
		

	#Force printing in stdout, regardless of the context (such as the one defined above)	
	def force_print(self, value):
		prev_stdout = sys.stdout
		sys.stdout = self._stdout
		print(value)
		sys.stdout = prev_stdout



def duplicatedir(src,dst):
	
	if not os.path.exists(src):
		print('ImagePipeline_utils. duplicatedir: Source directory does not exists!')
		return
	
	if src != dst:
		
		if os.path.exists(dst):
			shutil.rmtree(dst)

		shutil.copytree(src=src,dst=dst) 

def createdir_ifnotexists(directory):
	#create directory, recursively if needed, and do nothing if directory already exists
	os.makedirs(directory, exist_ok=True)

def initdir(directory):

	if os.path.exists(directory):
		shutil.rmtree(directory)   
	os.makedirs(directory)
			
def to_RGB(image):
	return image.convert('RGB')

def to_grayscale(image):	
	return image.convert('L')

def split_RGB_images(input_dir):
	
	imname = '*'
	orignames = glob(os.path.join(input_dir, imname))
	
	for orig in orignames:
		
		try:
			im = Image.open(orig)			

			#remove alpha component
			im = to_RGB(im)
			
			#split channels
			r, g, b = Image.Image.split(im)
			r = to_RGB(r)
			g = to_RGB(g)
			b = to_RGB(b)


			#save as png (and remove previous version)
			f, e = os.path.splitext(orig)
			os.remove(orig)
			
			r.save(f+"_red.png")
			g.save(f+"_green.png")
			b.save(f+"_blue.png")
			
		except Exception as e:
			print(e)	

def unsplit_RGB_images(input_dir):
	
	imname = '*_red.png'
	orignames = glob(os.path.join(input_dir, imname))
	
	for orig in orignames:
		
		try:
			substring = orig[:-8]
			r = to_grayscale(Image.open(substring+'_red.png'))
			g = to_grayscale(Image.open(substring+'_green.png'))
			b = to_grayscale(Image.open(substring+'_blue.png'))
			
			im = Image.merge('RGB', (r,g,b) )
			
			#save as png (and remove monochannel images)
			os.remove(substring+'_red.png')
			os.remove(substring+'_green.png')
			os.remove(substring+'_blue.png')
			
			im.save(substring+".png")
			
		except Exception as e:
			print(e)			
			
	
			
def preprocess(input_dir, gray = True, resize = True, size = (1000,1000)):

	imname = '*'
	orignames = glob(os.path.join(input_dir, imname))
	
	for orig in orignames:
		
		try:
			im = Image.open(orig)

			#remove alpha component
			im = to_RGB(im)

			#convert to grayscale
			if gray:
				im = to_grayscale(im)

			#resize
			if resize:

				width, height = im.size

				#resize only if larger than limit
				if width > size[0] or height > size[1]:
					im.thumbnail(size,Image.ANTIALIAS)

			#save as png (and remove previous version)
			f, e = os.path.splitext(orig)
			os.remove(orig)
			im.save(f+".png")
		except Exception as e:
			print(e)

def filtering(input_dir, median = True, median_winsize = 5, mean = True, mean_winsize = 5):

	with timing("Filtering (median) with PIL (consider using filtering_opencv for faster processing)"):
		imname = '*'
		orignames = glob(os.path.join(input_dir, imname))

		for orig in orignames:

			try:
				im = Image.open(orig)

				
				#median blur
				if median:
					im = im.filter(ImageFilter.MedianFilter(median_winsize))  
					
				#mean blur
				if mean:
					im = im.filter(ImageFilter.Meanfilter(mean_winsize))				 

				#save as png (and remove previous version)
				f, e = os.path.splitext(orig)
				os.remove(orig)
				im.save(f+".png")
			except Exception as e:
				print(e)

def filtering_opencv(input_dir, median = True, median_winsize = 5, gaussian = True, gaussian_x = 5, gaussian_y = 5, gaussian_std = 0, mean = True, mean_winsize = 3):

	with timing("Filtering (median) with opencv"):
		imname = '*'
		orignames = glob(os.path.join(input_dir, imname))

		for orig in orignames:
			print(orig)
			try:
				im = cv2.imread(orig, cv2.IMREAD_COLOR)


				#median blur
				if median:
					im = cv2.medianBlur(im,median_winsize)	 
					
				if gaussian:
					im = cv2.GaussianBlur(im,(gaussian_x,gaussian_y),gaussian_std)

				#mean blur
				if mean:
					im = cv2.blur(im,(mean_winsize,mean_winsize))
					
				

				#save as png (and remove previous version)
				f, e = os.path.splitext(orig)
				os.remove(orig)
				cv2.imwrite(f+".png", im)
			except Exception as e:
				print(e)
	
			
def rotate_images(input_dir):

	imname = '*'
	orignames = glob(os.path.join(input_dir, imname))
	
	for orig in orignames:
		
		try:
			im = Image.open(orig)

			#remove alpha component
			im = im.transpose(Image.ROTATE_90)

			#save as png (and remove previous version)
			f, e = os.path.splitext(orig)
			os.remove(orig)
			im.save(f+".png")
		except Exception as e:
			print(e)

def unrotate_images(input_dir):

	imname = '*'
	orignames = glob(os.path.join(input_dir, imname))
	
	for orig in orignames:
		
		try:
			im = Image.open(orig)

			#remove alpha component
			im = im.transpose(Image.ROTATE_270)

			#save as png (and remove previous version)
			f, e = os.path.splitext(orig)
			os.remove(orig)
			im.save(f+".png")
		except Exception as e:
			print(e)			
			
def reset_gpu(device = 0):  
	
	ncuda.select_device(device)
	ncuda.close()
	
import os, time, datetime
#import PIL.Image as Image
import numpy as np
from skimage.measure import compare_psnr, compare_ssim
from skimage.io import imread, imsave

def to_tensor(img):
	if img.ndim == 2:
		return img[np.newaxis,...,np.newaxis]
	elif img.ndim == 3:
		return np.moveaxis(img,2,0)[...,np.newaxis]

def from_tensor(img):
	return np.squeeze(np.moveaxis(img[...,0],0,-1))

def save_result(result,path):
	path = path if path.find('.') != -1 else path+'.png'
	ext = os.path.splitext(path)[-1]
	if ext in ('.txt','.dlm'):
		np.savetxt(path,result,fmt='%2.4f')
	else:
		imsave(path,np.clip(result,0,1))

fontfile = os.path.join(utilspath,"arial.ttf")

def addnoise(im, sigma = 10, imagetype = 'L', add_label = False):
	
	x = np.array(im)
	y = x + np.random.normal(0, sigma, x.shape)
	y=np.clip(y, 0, 255)
	
	im = PIL.Image.fromarray(y.astype('uint8'), imagetype)

	if add_label:
		d = ImageDraw.Draw(im)
		fnt = ImageFont.truetype(fontfile, 40)
		if imagetype == 'L':
			fill = 240
		elif imagetype == 'RGB':
			fill = (255, 0, 0)
		elif imagetype == 'RGBA':
			fill = (255,0,0,0)
		d.text((10,10), "sigma = %s" % sigma, font = fnt, fill = fill)

	return im


utilspath = os.path.join(os.getcwd(), 'utils/')

fontfile = os.path.join(utilspath,"arial.ttf")

def concat_images(img_list, labels = [], imagetype = None, sameheight = True, imagewidth = None, imageheight = None, labelsize = 30, labelpos = (10,10), labelcolor = None):

	"""
	imagetype: allow to convert all images to a PIL.Image.mode (L = grayscale, RGB, RGBA, ...)
	sameheight: put all images to same height (size of smallest image of the list, or imageheight if not None)
	imageheight: if not None, force all images to have this height (keep aspect ratio). Force sameheight to True
	imagewidth: if not None, force all images to have this width (keep aspect ratio if sameheight=False and imageheight=None)
	"""
	images = deepcopy(img_list)
	
	if imagetype == None:
		imagetype = 'RGB'
	
	images = [im.convert(imagetype) for im in images]
	
	#force all image to imageheight (keep aspect ratio)
	if imageheight is not None:
		sameheight = True
		
	widths, heights = zip(*(i.size for i in images))
	
	#resize needed ?
	if ( (len(set(heights)) > 1) & sameheight ) or (imageheight is not None) or (imagewidth is not None):
		
		if imageheight is None:
			imageheight = min(heights)

		#force all images to same width
		if imagewidth is not None:
			if sameheight: #force width and height
				images = [im.resize( (int(imagewidth),int(imageheight)),PIL.Image.ANTIALIAS ) for im in images]
			else: #force width (keep aspect ratio)
				images = [im.resize( (int(imagewidth),int(im.height*imagewidth/im.width)),PIL.Image.ANTIALIAS ) for im in images]
		else: #force height (keep aspect ratio)
			images = [im.resize( (int(im.width*imageheight/im.height), imageheight) ,PIL.Image.ANTIALIAS) for im in images]
			

	widths, heights = zip(*(i.size for i in images))
	total_width = sum(widths)
	max_height = max(heights)

	new_im = PIL.Image.new(imagetype, (total_width, max_height))

	#add labels to images
	if len(labels) == len(images):

		fnt = ImageFont.truetype(fontfile, labelsize)
		if imagetype == 'L':
			fill = 240
		elif imagetype == 'RGB':
			fill = (176,196,222)
		elif imagetype == 'RGBA':
			fill = (176,196,222,0)

		if labelcolor is not None:
			fill = labelcolor

		for i in range(len(labels)):
			d = ImageDraw.Draw(images[i]).text(labelpos, labels[i], font = fnt, fill = fill)

	x_offset = 0
	for im in images:
		new_im.paste(im, (x_offset,0))
		x_offset += im.size[0]
	
	return new_im

def display_images(im_list, labels = [], **kwargs):
	display(concat_images(im_list, labels, **kwargs))

def get_filepaths(directory):
	files = [os.path.join(directory, file) for file in os.listdir(directory) if os.path.isfile(os.path.join(directory, file))]
	return files

def get_filenames(directory):
	files = [file for file in os.listdir(directory) if os.path.isfile(os.path.join(directory, file))]
	return files

def display_folder(directory, limit = 10, **kwargs):
	
	files = get_filepaths(directory)
	files.sort()
	if len(files) > limit:
		files = files[:limit]
	
	display_images([PIL.Image.open(f) for f in files], [os.path.split(f)[1] for f in files], **kwargs)

def compare_folders(dirs, labels = [], **kwargs):

	if type(dirs) is list:
		#dirs is a list of folders containings processed images to compare
		dirlist = dirs
		
	elif type(dirs) is str:
		#dirs if parent folder of subfolders containings processed images to compare
		dirlist = glob(os.path.join(dirs,'*'))
		dirlist = [d for d in dirlist if os.path.isdir(d)]

	first_dir = dirlist[0]
	names = get_filenames(first_dir)
	names.sort()
	for n in names:
		paths = [glob(os.path.join(d,osp.splitext(n)[0]+'*'))[0] for d in dirlist]
		display_images([PIL.Image.open(p) for p in paths], [os.path.split(d)[1] for d in dirlist], **kwargs)


def clone_git(url, dir_name = None, tag = None, reclone = False):

	"""	
	url: url of the git repository to clone
	dir_name: name of the folder to give to the repository. If not given, the git repository name is used
	tag: allows to checkout a specific commit if given
	reclone: overwrite existing repo
	"""
	
	old_dir = os.getcwd()
	
	if dir_name is None:		
		dir_name = os.path.split(url)[1] #use git repo name
		dir_name = os.path.splitext(dir_name)[0] #remove ".git" if present
	
	if reclone and os.path.exists(dir_name):
		shutil.rmtree(dir_name)
		
	if not os.path.exists(dir_name):
		command = "git clone %s %s" % (url, dir_name)
		subprocess.run(command, shell = True)
		
	os.chdir(dir_name)
	
	if tag is not None:
		command = "git checkout %s" % tag
		subprocess.run(command, shell = True)
	
	git_path = os.path.join(os.getcwd())
	
	os.chdir(old_dir)
	
	return git_path

def download_gdrive(file_id):
	
	subprocess.run("wget https://raw.githubusercontent.com/GitHub30/gdrive.sh/master/gdrive.sh", shell = True)
	subprocess.run("curl gdrive.sh | bash -s %s" % file_id, shell = True)
	subprocess.run("rm gdrive.sh", shell = True)
	
def image_average(imlist, weights):
	
	assert len(imlist)==len(weights), "Input lists should have same size."
	weights = np.array(weights)
	weights = weights/np.sum(weights)
	
	# Assuming all images are the same size, get dimensions of first image
	w,h=Image.open(imlist[0]).convert("RGB").size
	N=len(imlist)

	# Create a numpy array of floats to store the average (assume RGB images)
	arr=np.zeros((h,w,3),np.float)

	# Build up average pixel intensities, casting each image as an array of floats
	for im in imlist:
		imarr=np.array(Image.open(im),dtype=np.float)
		arr=arr+imarr/N

	# Round values in array and cast as 8-bit integer
	arr=np.array(np.round(arr),dtype=np.uint8)

	# Generate, save and preview final image
	out=Image.fromarray(arr,mode="RGB")
	
	return out
