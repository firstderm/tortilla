#!/usr/bin/env python
"""
Converts dataset from folder-subfolder format (one subfolder per class) to
tortilla's data format
"""

import glob
import os
from PIL import Image
import shutil
from utils import *
import numpy as np
import uuid
import json
import random
import multiprocessing
from functools import partial

def preprocessing(_class, meta):

	train_class_frequency = {}
	val_class_frequency = {}

	train_class_frequency[_class] = 0
	val_class_frequency[_class] = 0

	train_list = []
	val_list = []
	error_list = []
	files = []

	files.extend(glob.glob(os.path.join(meta["input_folder_path"],_class,"*")))
	random.shuffle(files)

	for _idx, _file in enumerate(files):
		if not meta["non_interactive_mode"]:
			print("Processing {}/{} :: {}".format(str(_idx), str(len(files)), _file))
		_class = _file.split("/")[-2]

		# Stop processing of this class if above max_images_per_class
		if train_class_frequency[_class]+val_class_frequency[_class] == meta["max_images_per_class"]:
			#print("Max Images reached for the class {}".format(class))
			continue

		# Open, Preprocess and write file to output_folder_path
		try:
			# TODO: Make this opening of the file optional
			im = Image.open(_file).convert('RGB')
			if not meta["no_copy"]:
				im = im.resize(meta["img_size"])
		except Exception as e:
			error_list.append((_file, str(_class), str(e)))
			continue

		is_train = np.random.rand() <= meta["train_percent"]

		"""
		In no_copy mode, the files are not copied over,
		and it is assumed that the files are in the correct size

		"""
		if not meta["no_copy"]:
			target_file_name = "{}_{}".format(
				str(uuid.uuid4()),
				"_".join(_file.split("/")[-1].split())
				)
			# Absolute Path
			target_file_path = os.path.abspath(os.path.join(
				meta["output_folder_path"],
				"images",
				_class,
				target_file_name
			))
			# File path relative to the images root
			target_file_path_rel = os.path.join(
				"images",
				_class,
				target_file_name
			)
			im.save(target_file_path)
		else:
			target_file_name = os.path.basename(_file)
			target_file_path = os.path.abspath(_file)

		# Conditionally save absolute paths to the file
		# Useful when designing multiple experiments on the same dataset
		if not meta["is_absolute_path"]:
			if meta["no_copy"]:
				raise Exception(
				"""It seems that both `no_copy` mode is active
				while `absolute_path` mode is not. `no_copy` mode is currently
				only supported while the `absolute_path` mode is on. Please pass
				both the `--absolute-path --no-copy` flags together.
				"""
				)
			else:
				target_file_path = target_file_path_rel

		if is_train:
			train_list.append((target_file_path, str(meta["classes"].index(_class))))
			train_class_frequency[_class] += 1
		else:
			val_list.append((target_file_path, str(meta["classes"].index(_class))))
			val_class_frequency[_class] += 1

	return (train_list, val_list, train_class_frequency, val_class_frequency, error_list)


def multiple_preprocessing(classes, meta):
	p = multiprocessing.Pool(meta["num_cpu"])
	preprocess = partial(preprocessing, meta = meta)

	tuples=p.map(preprocess, classes)
	t_list, v_list,t_freq, v_freq, e_list = zip(*tuples)

	t_list = [ent for sublist in t_list for ent in sublist]
	v_list = [ent for sublist in v_list for ent in sublist]
	e_list = [ent for sublist in e_list for ent in sublist]

	t_freq = { c: freq for d in t_freq for c, freq in d.items() }
	v_freq = { c: freq for d in v_freq for c, freq in d.items() }

	return t_list, v_list, e_list, t_freq, v_freq


if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
			description="Converts dataset from folder-subfolder format \
						(one sub folder per class) to tortilla's data format")

	parser.add_argument('--input-folder-path', action='store', dest='input_folder_path',
						required=True,
						help='Path to input folder containing images')
	parser.add_argument('--output-folder-path', action='store', dest='output_folder_path',
						required=True,
						help='Path to output folder to write images')
	parser.add_argument('--min-images-per-class', action='store', dest='min_images_per_class',
						default=50,
						help='Minimum number of images required per class')
	parser.add_argument('--max-images-per-class', action='store', dest='max_images_per_class',
						default=5000,
						help='Maximum number of images required per class')
	parser.add_argument('--train-percent', action='store', dest='train_percent',
						default=0.8,
						type=float,
						help='Percentage of all images to use as training data')
	parser.add_argument('--dataset-name', action='store', dest='dataset_name',
						required=True,
						help='Name of the Dataset')
	parser.add_argument('--img-size', action='store', dest='img_size',
						default="256x256",
						help='Size of the target images')
	parser.add_argument('--num-cpu', action='store', dest='num_cpu',
						default=multiprocessing.cpu_count(),
						help='Number of cores to use for prepare_data')
	parser.add_argument('--absolute-path', dest='absolute_path', action='store_true')
	parser.add_argument('--no-copy', dest='no_copy', action='store_true')
	parser.add_argument('--non-interactive-mode', dest='non_interactive_mode', action='store_true')


	args = parser.parse_args()

	input_folder_path = args.input_folder_path
	output_folder_path = args.output_folder_path
	min_images_per_class = int(args.min_images_per_class)
	max_images_per_class = int(args.max_images_per_class)
	train_percent = float(args.train_percent)
	dataset_name = args.dataset_name
	img_size = (int(args.img_size.split("x")[0]), int(args.img_size.split("x")[1]))
	absolute_path = args.absolute_path
	no_copy = args.no_copy
	non_interactive_mode = args.non_interactive_mode
	num_cpu = int(args.num_cpu)

	"""
	Validation Input and Output Folder
	"""
	classes = get_classes_from_input_folder(input_folder_path, non_interactive_mode)
	classes = min_images_validation(input_folder_path, classes, min_images_per_class)
	output_folder_path_validation(output_folder_path, classes, non_interactive_mode)


	_message = """
		Input Folder Path : {}
		Output Folder Path : {}
		Minimum Images per Class : {}
		Maximum Images per Class : {}
		Train Percentage : {}
		Dataset Name : {}
		Target Image Size : {}
		Number of Classes : {}

		Proceed with these parameters ?
	""".format(
		input_folder_path,
		output_folder_path,
		min_images_per_class,
        max_images_per_class,
		train_percent,
		dataset_name,
		img_size,
		len(classes)
	)

	response = query_yes_no(_message, default="yes",non_interactive_mode=non_interactive_mode)
	if not response:
		exit(0)

	"""
	Store arguments
	"""
	_meta = {}
	_meta["dataset_name"] = dataset_name
	_meta["train_percent"] = train_percent
	_meta["input_folder_path"] = os.path.abspath(input_folder_path)
	_meta["output_folder_path"] = os.path.abspath(output_folder_path)
	_meta["min_images_per_class"] = min_images_per_class
	_meta["max_images_per_class"] = max_images_per_class
	_meta["img_size"] = img_size
	_meta["is_absolute_path"] = absolute_path
	_meta["no_copy"] = no_copy
	_meta["total_classes"] = len(classes)
	_meta["classes"] = classes
	_meta["non_interactive_mode"] = non_interactive_mode
	_meta["num_cpu"] = num_cpu

	"""
	Actual Preprocessing starts
	"""

	rough_class_frequency = quick_compute_class_frequency_from_folder(
				input_folder_path, classes)

	train_list, val_list, error_list, train_class_frequency, val_class_frequency = multiple_preprocessing(classes=classes, meta=_meta)

	"""
	Aggregate results
	"""
	_meta["total_images"] = len(train_list) + len(val_list)
	_meta["errors"] = len(error_list)
	_meta["train_class_frequency"] = train_class_frequency
	_meta["val_class_frequency"] = val_class_frequency

	# Write meta file
	f = open(os.path.join(
		output_folder_path,
		"meta.json"
	), "w")
	f.write(json.dumps(
					_meta,
					sort_keys=True,
					indent=4,
					separators=(',', ': ')
					))

	# Write classes.txt
	f = open(os.path.join(
		output_folder_path,
		"classes.txt"
	), "w")
	f.write("\n".join(classes))

	# Write train.json
	f = open(os.path.join(
		output_folder_path,
		"train.json"
	), "w")
	_train = {}
	_train = {item[0]: item[1] for item in train_list}
	f.write(json.dumps(
					_train,
					sort_keys=True,
					indent=4,
					separators=(',', ': ')
					))

	# Write val.json
	f = open(os.path.join(
		output_folder_path,
		"val.json"
	), "w")
	_val = {}
	_val = {item[0]: item[1] for item in val_list}
	f.write(json.dumps(
					_val,
					sort_keys=True,
					indent=4,
					separators=(',', ': ')
					))

	# Write errors.txt
	f = open(os.path.join(
		output_folder_path,
		"error.txt"
	), "w")
	error_list = ["\t".join(x) for x in error_list]
	f.write("\n".join(error_list))
