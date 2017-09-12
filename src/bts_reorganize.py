# Brain Tumor Segmentation
# Script for Reorganizing
# Author: Qixun Qu
# Date: 2017/09/12

'''

Class BTSReorganize

Reorganize volumes from source folder
to target folder as shown below.

Source folder:
----- BRATS2015_Training
  |----- HGG
     |----- brats_xxxx_patxxxx_xxxx
        |----- VSD.Brain.XX.O.MR_Flair.xxxxx
           |----- VSD.Brain.XX.O.MR_Flair.xxxxx.mha
        |----- VSD.Brain.XX.O.MR_T1.xxxxx
           |----- VSD.Brain.XX.O.MR_T1.xxxxx.mha
        |----- VSD.Brain.XX.O.MR_T1c.xxxxx
           |----- VSD.Brain.XX.O.MR_T1c.xxxxx.mha
        |----- VSD.Brain.XX.O.MR_T2.xxxxx
           |----- VSD.Brain.XX.O.MR_T2.xxxxx.mha
        |----- VSD.Brain_3more.XX.O.OT.xxxxx
           |----- VSD.Brain_3more.XX.O.OT.xxxxx.mha
  |----- LGG
     |----- (same structure as HGG)

220 samples in HGG, 54 volumes in LGG.

Target Folder:
----- data
  |----- HGG
     |----- xxx
        |----- xxx_Flair.mha
        |----- xxx_T1.mha
        |----- xxx_T1c.mha
        |----- xxx_T2.mha
        |----- xxx_Mask.mha
  |----- LGG
     |----- (same structure as HGG)

xxx is from 0 to 219 in HGG,
and from 0 to 53 in LGG.

'''



import os
from tqdm import *
from shutil import copy
from bts_settings import *



class BTSReorganize():

    def __init__(self, input_dir, output_dir):

        self._reorganize(input_dir, output_dir)

        return


    def _reorganize(self, input_dir, output_dir):

        sub_target = os.listdir(input_dir)

        for st in sub_target:
            print("Starting copy files in ", st)
            to_path = os.path.join(output_dir, st)
            from_path = os.path.join(input_dir, st)
            from_dirs = os.listdir(from_path)

            if not os.path.isdir(to_path):
                os.makedirs(to_path)

            n = 0
            for d in tqdm(from_dirs):
                sub_to_path = os.path.join(to_path, str(n))
                sub_from_path = os.path.join(from_path, d)
                sub_from_dirs = os.listdir(sub_from_path)

                if not os.path.isdir(sub_to_path):
                    os.makedirs(sub_to_path)

                i = 0
                for sd in sub_from_dirs:
                    sub_sub_from_path = os.path.join(sub_from_path, sd)
                    source_files = os.listdir(sub_sub_from_path)

                    for sf in source_files:
                        if sf.endswith(".mha"):
                            source_file = sf

                    source_path = os.path.join(sub_sub_from_path, source_file)

                    target_file = str(n) + "_" + VOLUME_NAMES[i] + ".mha"
                    target_path = os.path.join(sub_to_path, target_file)
                    copy(source_path, target_path)

                    i += 1

                n += 1

        print("Done")

        return



if __name__ == "__main__":

    input_dir = "E:\\Data\\Brain\\BRATS2015_Training"
    output_dir = "E:\\ms\\data"
    BTSReorganize(input_dir, output_dir)