# Brain Tumor Classification
# Script for Preprocessing
# Author: Qixun Qu
# Create on: 2017/09/10
# Modify on: 2017/11/28

#     ,,,         ,,,
#   ;"   ';     ;'   ",
#   ;  @.ss$$$$$$s.@  ;
#   `s$$$$$$$$$$$$$$$'
#   $$$$$$$$$$$$$$$$$$
#  $$$$P""Y$$$Y""W$$$$$
#  $$$$  p"$$$"q  $$$$$
#  $$$$  .$$$$$.  $$$$'
#   $$$DaU$$O$$DaU$$$'
#    '$$$$'.^.'$$$$'
#       '&$$$$$&'

'''

Class BTCPreprocess

-1- Correct bias field via N4BiasFieldCorrection.
-2- Intensity normalization on each volume.
-3- Merge four volumes (flair, t1, t1Gd and t2) into one volume
    and remove surrounding backgrounds to keep minimum volume.


Pipline of Preprocessing:

           Generate All Paths from Input Folder
      Generate Folders for Temporary and Output Files
                            |
    --------------------------------------------------
    |      |      |      |      |      |      |      |
  N4ITK  N4ITK  N4ITK  N4ITK  N4ITK  N4ITK  N4ITK  N4ITK  <=== Multi-process of
    |      |      |      |      |      |      |      |         N4BiasFieldCorrection
    --------------------------------------------------
                            |
              Save Outputs in Temporary Folder
                            |
                -------------------------
                |       |       |       |
              Flair    T1      T1c     T2  <=== Multi-process of
                |       |       |       |       Intensity Normalization
                -------------------------
                            |
              Save Outputs in Temporary Folder
                            |
    --------------------------------------------------
    |      |      |      |      |      |      |      |
  Merge  Merge  Merge  Merge  Merge  Merge  Merge  Merge  <=== Multi-process of
    &      &      &      &      &      &      &      &         Merge four types volumes into
  Save   Save   Save   Save   Save   Save   Save   Save        one volume, remove surrounding
    |      |      |      |      |      |      |      |         backgrounds and save outputs
    --------------------------------------------------
                            |
              Save Outputs in Output Folder
                 Delete Tempprary Folder

'''


from __future__ import print_function

import os
import shutil
import numpy as np
import pandas as pd
import nibabel as nib
from btc_settings import *
from multiprocessing import Pool, cpu_count
from nipype.interfaces.ants.segmentation import N4BiasFieldCorrection


# Helper function to do multiprocessing of
# BTCPreprocess._bias_field_correction
def unwrap_bias_field_correction(arg, **kwarg):
    return BTCPreprocess._bias_field_correction(*arg, **kwarg)


# Helper function to do multiprocessing of
# BTCPreprocess._intensity_normalization
def unwrap_intensity_normalization(arg, **kwarg):
    return BTCPreprocess._intensity_normalization(*arg, **kwarg)


# Helper function to do multiprocessing of
# BTCPreprocess._merge_to_one_volume
def unwrap_merge_to_one_volume(arg, **kwarg):
    return BTCPreprocess._merge_to_one_volume(*arg, **kwarg)


class BTCPreprocess():

    def __init__(self, input_dir, output_dir, temp_dir="temp", preprocess=True):
        '''__INIT__

            Initialization of class BTCPreprocess, and finish
            preprocessing of all brain volumes.

            The structure as follows:
            - Create folders to keep temporary files and save
              output files which has been preprocessed.
            - Multiprocess of function to correct bias field.
            - Multiprocess of function to normalize intensity.
            - Multiprocess of function to merge and save output.
            - Delete all temporary files.

            Inputs:
            -------
            - input_dir: path of the directory which
                         keeps original volumes
            - output_dir: path of the directory which
                          outputs will be saved in
            - temp_dir: path of the directory which
                        keeps temporary files during the
                        preprocessing, default is "temp"

        '''

        # Serial numbers of patients generated by btc_reorganize.py
        self.volume_no = os.listdir(input_dir)

        # Output folder of mask volumes
        self.mask_folder = os.path.join(output_dir, MASK_FOLDER)
        # Output folder of ensemble volumes
        self.full_folder = os.path.join(output_dir, FULL_FOLDER)

        # Preprocess pipline
        self._create_folders(temp_dir)
        self._bias_field_correction_multi(input_dir, temp_dir)
        self._intensity_normalization_multi(temp_dir)
        self._merge_to_one_volume_multi(input_dir, temp_dir)

        # Delete temporary folder and all files in it
        self._delete_temp_files(temp_dir)

        return

    def _create_folders(self, temp_dir):
        '''_CREATE_FOLDERS

            Create folders for temporary files and outputs.
            All folders are as below.

            Folder for temporary files:
            ----- temp_dir (default is "temp")
              |----- flair
              |----- t1
              |----- t1Gd
              |----- t2

            Folders for outputs:
            ----- self.output_dir
              |----- full
              |----- mask

            Input:
            ------
            - temp_dir: path of the directory which
                        keeps temporary files during the
                        preprocessing, default is "temp"

            The other two arguments, self.mask_folder and
            self.full_folder has already assigned while
            the instance is initialized.

        '''

        if not os.path.isdir(temp_dir):
            os.makedirs(temp_dir)

        for name in VOLUME_TYPES:
            sub_temp_dir = os.path.join(temp_dir, name)
            if not os.path.isdir(sub_temp_dir):
                os.makedirs(sub_temp_dir)

        if not os.path.isdir(self.mask_folder):
            os.makedirs(self.mask_folder)

        if not os.path.isdir(self.full_folder):
            os.makedirs(self.full_folder)

        return

    def _bias_field_correction_multi(self, input_dir, temp_dir):
        '''_BIAS_FIELD_CORRECTION_MULTI

            Main function of bias field correctgion to map tasks
            on different cpus to accelerate processing speed.
            The number of subprocesses equals to the number of cpus.

            - Generate paths of all original volumes and
              paths of temporary volumes that will be corrected.
            - Map pairs of paths (original path and temporary path)
              to function BTCPreprocess._bias_field_correction.

            Inputs:
            -------
            - input_dir: path of the directory which
                         keeps original volumes
            - temp_dir: path of the directory which
                        keeps temporary files during the
                        preprocessing, default is "temp"

        '''

        orig_volumes_path = []  # paths of original volumes
        temp_volumes_path = []  # paths of temporary volumes
        for vtype in VOLUME_TYPES:
            for vno in self.volume_no:
                file_name = vno + "_" + vtype + SOURCE_EXTENSION
                orig = os.path.join(input_dir, vno, file_name)
                temp = os.path.join(temp_dir, vtype, file_name)
                orig_volumes_path.append(orig)
                temp_volumes_path.append(temp)

        print("Stage 1: Bias Field Correction\n")
        paras = zip([self] * len(orig_volumes_path),
                    orig_volumes_path,
                    temp_volumes_path)
        pool = Pool(processes=cpu_count())
        pool.map(unwrap_bias_field_correction, paras)

        return

    def _bias_field_correction(self, orig_path, temp_path):
        '''_BIAS_FIELD_CORRECTION

            Apply N4BiasFieldCorrection method on a volume
            and save the output into temporary folder.
            Settings can be found in btc_settings.py.

            Original paper can be found here:
            https://www.ncbi.nlm.nih.gov/pubmed/20378467

            Inputs:
            -------
            - orig_path: path for original volume
            - temp_path: path for temporary volume which is
                         the output of bias field correction

            --- NOTE ---

            This function has been tested to deal with .nii.gz files
            both in Windows 7 and Ubuntu 16.04. It is necessary to
            install or compile ANTs first.

            For Windows:
            Download ANTs 2.1 for Windows from this link:
            https://github.com/ANTsX/ANTs/releases.
            Extract files in to folder, and add this folder's path
            into system path.

            For Ubuntu:
            Download source code from here:
            https://github.com/ANTsX/ANTs.
            Compile ANTs as instructions shown in:
            https://github.com/ANTsX/ANTs/wiki/Compiling-ANTs-on-Linux-and-Mac-OS.

        '''

        print("N4ITK on: " + orig_path)
        n4 = N4BiasFieldCorrection()

        n4.inputs.input_image = orig_path
        n4.inputs.output_image = temp_path

        n4.inputs.dimension = N4_DIMENSION
        n4.inputs.n_iterations = N4_ITERATION
        n4.inputs.shrink_factor = N4_SHRINK_FACTOR
        n4.inputs.convergence_threshold = N4_THRESHOLD
        n4.inputs.bspline_fitting_distance = N4_BSPLINE

        # Run command line silently in UBUNTU
        n4.run()

        # Run command line in WINDOWS
        # Do not forget import denpendicy at the head of script
        # import subprocess

        # Run command line with information printing in WINDOWS
        # subprocess.call(n4.cmdline.split(" "))

        # Run command line silently in WINDOWS
        # devnull = open(os.devnull, 'w')
        # subprocess.call(n4.cmdline.split(" "), stdout=devnull, stderr=devnull)

        return

    def _intensity_normalization_multi(self, temp_dir):
        '''_INTENSITY_NORMALIZATION_MULTI

            Main function of intensity normalization to map tasks
            on different cpus to accelerate processing speed.
            The number of subprocesses equals to the number of cpus.

            Input:
            ------
            - temp_dir: path of the temporary directory that outputs
                        of bias field correction have been saved in

        '''

        print("Stage 2: Intensity Normalization\n")
        paras = zip([self] * len(VOLUME_TYPES),
                    [temp_dir] * len(VOLUME_TYPES),
                    VOLUME_TYPES)
        pool = Pool(processes=cpu_count())
        pool.map(unwrap_intensity_normalization, paras)

        return

    def _intensity_normalization(self, temp_dir, vtype):
        '''_INTENSITY_NORMALIZATION

            Apply intensity normalization on each type of volumes.
            (There are four types volumes: Flair, T1, T1c and T2.)
            Compute landmarks for Flair, T1, T1c and T2 respectively.
            Obtain intensities at certain percentiles from each volume.
            Transform each volume intensity according to corresponding
            landmarks.

            Original paper can be found here:
            http://ieeexplore.ieee.org/abstract/document/836373/

            Inputs:
            -------
            - temp_dir: path of temporary folder which keeps the outputs
                        of bias field correction
            - vtype: types of volume, flair, t1, t1GD or t2

        '''

        # Compute landmarks for each type volumes
        landmarks, all_volume_pct = self._get_volume_landmarks(temp_dir, vtype)

        # Save landmarks into csv files
        landmarks_dict = dict(zip(PCTS_COLUMNS, landmarks))
        landmarks_df = pd.DataFrame(data=landmarks_dict, columns=PCTS_COLUMNS, index=[0])
        landmarks_df.to_csv(os.path.join(temp_dir, vtype + "_landmarks.csv"))

        # Transform volumes' intensity
        self._intensity_transform(temp_dir, vtype, landmarks, all_volume_pct)

        return

    def _get_volume_landmarks(self, temp_dir, vtype):
        '''_GET_VOLUME_LANDMARKS

            Take Flair volumes as example.
            - Extract values from each volume at centain percentiles,
              PCTS, which is assigned in btc_settings.py.
            - Ensemble volumes' percentile values into one array.
            - Compute the mean percentile values as the landmarks
              of all Flair volumes.

            Inputs:
            -------
            - temp_dir: path of temporary folder which keeps the outputs
                        of bias field correction
            - vtype: types of volume, flair, t1, t1Gd or t2

            Outputs:
            --------
            - landmarks: mean percentile values of a certain type volumes
            - all_volume_pct: percentile values of all volumes in one type

        '''

        print("Compute landmarks of all " + vtype + " volumes")
        all_volume_pct = []
        for vno in self.volume_no:
            # Load bias-corrected volume
            file_name = vno + "_" + vtype + SOURCE_EXTENSION
            path = os.path.join(temp_dir, vtype, file_name)
            volume = nib.load(path).get_data()

            # Check whether volume's background has the minimum intensity
            # If not, set the background to the minimum intensity
            volume_min = np.min(volume)
            if volume_min < 0:
                volume[np.where(volume == 0)] = volume_min
                volume = volume - np.min(volume)

            # Sort voxels by their intensities except background,
            # which makes it easy to compute percentile values
            volume = volume[np.where(volume > 0)]
            sort = np.sort(volume)
            sort_len = len(sort)

            # Compute percentile values of one volume
            one_volume_pct = []
            for p in PCTS:
                pct_idx = int(np.ceil(p * sort_len)) - 1
                if pct_idx < 0:
                    pct_idx = 0
                one_volume_pct.append(sort[pct_idx])

            # Ensembel all volumes' percentile values into one array
            all_volume_pct.append(one_volume_pct)

        # Compute mean as landmarks of one certain type volume
        all_volume_pct = np.array(all_volume_pct)
        landmarks = np.mean(all_volume_pct, axis=0)

        return landmarks, all_volume_pct

    def _intensity_transform(self, temp_dir, vtype, landmarks, pct):
        '''_INTENSITY_TRANSFORM

            Transfor voxels' intensities according to the landmarks.
            For each volume, there are three classes voxels:
            - 1. voxels have higher intensities than its maximum percentile value;
            - 2. voxels have lower intensities than its minimum percentile value;
            - 3. voxels have proper intensities.

            Replace voxels 1 by the maximum value of landmarks.
            Set voxels 2 to background value which is 0.
            For voxels 3, transform intensitied to new percentile values
            as landmarks via interpolation.

            Inputs:
            -------
            - temp_dir: path of temporary folder which keeps the outputs
                        of bias field correction
            - vtype: types of volume, Flair, T1, T1c or T2
            - landmarks: new percentile values computed from
                         all volumes of a certain type
            - pct: original percentile values of volumes of a certain type

        '''

        print("Transform intensity of all " + vtype + " volumes")
        for i in range(len(self.volume_no)):
            # Load bias-corrected volume
            file_name = self.volume_no[i] + "_" + vtype + SOURCE_EXTENSION
            path = os.path.join(temp_dir, vtype, file_name)
            volume = nib.load(path).get_data()

            # Check whether volume's background has the minimum intensity
            # If not, set the background to the minimum intensity
            volume_min = np.min(volume)
            if volume_min < 0:
                volume[np.where(volume == 0)] = volume_min
                volume = volume - np.min(volume)

            # Indices of voxels whose intensities are
            # higher than its own maximum percentile value,
            # regard them as higher-voxels
            higher_idx = np.where(volume >= pct[i, -1])
            # Indices of voxels whose intensities are
            # lower than its own minimum percentile value,
            # regard them as lower-voxels
            lower_idx = np.where(volume < pct[i, 0])
            # Indices of voxels that are not background
            non_bg_idx = np.where(volume > 0)

            # Transform foreground voxels to new intensities
            volume[non_bg_idx] = np.interp(volume[non_bg_idx], pct[i, :], landmarks)
            # Set maximum percentile value of landmarks to higher-voxels
            volume[higher_idx] = landmarks[-1]
            # Set 0 to lower-voxels
            volume[lower_idx] = 0

            # Save transformed volumes into temporary folder
            file_name = self.volume_no[i] + "_" + vtype + TARGET_EXTENSION
            np.save(os.path.join(temp_dir, vtype, file_name), volume)

        print(vtype + ": Done")

        return

    def _merge_to_one_volume_multi(self, input_dir, temp_dir):
        '''_MERGE_TO_ONE_VOLUME_MULTI

            Main function of merging four types volumes and saving outputs
            to map tasks on different cpus to accelerate processing speed.
            The number of subprocesses equals to the number of cpus.

            Inputs:
            -------
            - input_dir: path of the directory which keeps mask volumes
            - temp_dir: path of temporary folder which keeps the outputs
                        of intensity transformation

        '''

        print("Stage 3: Merge flair, t1, t1Gd and t2 into One Volume")
        volume_no_len = len(self.volume_no)
        paras = zip([self] * volume_no_len,
                    [input_dir] * volume_no_len,
                    [temp_dir] * volume_no_len,
                    self.volume_no)
        pool = Pool(processes=cpu_count())
        pool.map(unwrap_merge_to_one_volume, paras)

        return

    def _merge_to_one_volume(self, input_dir, temp_dir, vno):
        '''_MERGE_TO_ONE_VOLUME

            Merge normalized flair, t1, t1Gd and t2 volumes of one patient
            to one volume. Remove surrounding backgrounds, and save output
            into output folder as the result of preprocessing.

            Inputs:
            -------
            - input_dir: path of the directory which keeps mask volumes
            - temp_dir: path of temporary folder which keeps the outputs
                        of intensity transformation
            - vno: serial number of volumes, which is also the folder name
                   of one patient's volumes

        '''

        print("NO." + vno + ": Save brain volume and mask volume")
        full_volume = np.zeros(FULL_SHAPE)
        for i in range(len(VOLUME_TYPES)):
            # Load intensity-transformed volume
            file_name = vno + "_" + VOLUME_TYPES[i] + TARGET_EXTENSION
            path = os.path.join(temp_dir, VOLUME_TYPES[i], file_name)
            volume = np.load(path)
            volume = np.rot90(volume, 3, axes=(0, 1))
            # Normalize the volue
            # volume = self._normalization(volume)
            # full_volume[..., 0] <== flair volume
            # full_volume[..., 1] <== t1 volume
            # full_volume[..., 2] <== t1Gd volume
            # full_volume[..., 3] <== t2 volume
            full_volume[..., i] = volume

        # Load relevant mask
        mask_path = os.path.join(input_dir, vno, vno + "_" + MASK_NAME + SOURCE_EXTENSION)
        mask_volume = nib.load(mask_path).get_data()
        mask_volume = np.rot90(mask_volume, 3, axes=(0, 1))

        # Remove surrounding backgrounds from ensemble volume and mask volume
        full_volume, mask_volume = self._keep_minimum_volume(full_volume, mask_volume)

        # Save volume into output folders
        full_volume_path = os.path.join(self.full_folder, vno + TARGET_EXTENSION)
        mask_volume_path = os.path.join(self.mask_folder, vno + TARGET_EXTENSION)

        np.save(full_volume_path, full_volume)
        np.save(mask_volume_path, mask_volume)

        return

    def _normalization(self, volume):
        '''_NORMALIZATION

            Normalize the input volume by substract its mean
            and diveded by its standard deviation.
            Background will not be taken into consideration.

            Input:
            ------
            - volume: the volume needs to be normalized

            Output:
            -------
            - normalized volume

        '''

        # Compute mean and std of foreground object
        non_zero_index = np.where(volume > np.min(volume))
        volume_mean = np.mean(volume[non_zero_index])
        volume_std = np.std(volume[non_zero_index])

        return (volume - volume_mean) / volume_std

    def _keep_minimum_volume(self, full, mask):
        '''_KEEP_MINIMUM_VOLUME

            Remove surrounding backgrounds from ensemble volume
            and mask volume to keep the minimum volume.
            Based on input volumes, compute the range of indices
            of three axes, extract sub-volume and return it back.

            Inputs:
            -------
            - full: ensemble volume
            - mask: relevant mask volume

            Outputs:
            --------
            - new_full: new ensemble volume after being processed
            - new_mask: new mask volume after being processed

        '''

        # Function to extract sub-array from given array
        # according to ranges of indices of three axes
        def sub_array(arr, index_begin, index_end):
            return arr[index_begin[0]:index_end[0],
                       index_begin[1]:index_end[1],
                       index_begin[2]:index_end[2]]

        # Compute background value of volume
        full_sum = np.sum(full, axis=3)
        min_full_sum = np.min(full_sum)

        # Compute range of indices of each axes
        non_bg_index = np.where(full_sum > min_full_sum)
        dims_begin = [np.min(nzi) for nzi in non_bg_index]
        dims_end = [np.max(nzi) + 1 for nzi in non_bg_index]

        # Add a bit more space around the minimum brain volume
        for i in range(len(dims_begin)):
            dims_begin[i] = dims_begin[i] - EDGE_SPACE
            # if the beginning index is lower than 0
            if dims_begin[i] < 0:
                dims_begin[i] = 0
            dims_end[i] = dims_end[i] + EDGE_SPACE
            # if the ending index is larger than the maximum index
            if dims_end[i] > BRAIN_SHAPE[i] - 1:
                dims_end[i] = BRAIN_SHAPE[i] - 1

        # Obtain sub-volumes from input volumes
        new_full = sub_array(full, dims_begin, dims_end)
        new_full = new_full.astype(np.float32)
        new_mask = sub_array(mask, dims_begin, dims_end)

        return new_full, new_mask

    def _delete_temp_files(self, temp_dir):
        '''_DELETE_TEMP_FILES

            Delete temporary files in temporary folder except
            the csv file of landmarks.

            Input:
            ------
            - temp_dir: path of temporary folder

        '''

        sub_temp_dirs = os.listdir(temp_dir)
        for std in sub_temp_dirs:
            path = os.path.join(temp_dir, std)
            # Delete all directories
            if os.path.isdir(path):
                shutil.rmtree(path)

        return


if __name__ == "__main__":

    parent_dir = os.path.dirname(os.getcwd())

    input_dir = os.path.join(parent_dir, DATA_FOLDER, ORIGINAL_FOLDER)
    output_dir = os.path.join(parent_dir, DATA_FOLDER, PREPROCESSED_FOLDER)
    temp_dir = os.path.join(TEMP_FOLDER, PREPROCESSED_FOLDER)
    BTCPreprocess(input_dir, output_dir, temp_dir, preprocess=True)
