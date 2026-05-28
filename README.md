## Wyoming landowner tags assessment
-----

Author: Guy Litt
Wyoming chapter of Backcountry Hunters & Anglers

This is a facts-based assessment of Wyoming's current landowner tag system based on tag allocation data published by the Wyoming Game and Fish Department.

It retrieves data from the WY G&F 2025 draw odds page, considering the total quota of type 1 tags and how many went to landowners.

To view some simple distributions of tag allocations to landowners, check out the *.ipynb files, e.g. 
 - [LandownerElkTags.ipynb](https://github.com/glitt13/public_trust_wildlife/blob/main/LandownerElkTags.ipynb)
 - [LandownerDeerTags.ipynb](https://github.com/glitt13/public_trust_wildlife/blob/main/LandownerDeerTags.ipynb)
 - [LandownerAntelopeTags.ipynb](https://github.com/glitt13/public_trust_wildlife/blob/main/LandownerAntelopeTags.ipynb)

As of February, 2026 data are hosted on tiiny.site. If the links don't work, get in touch with Guy to view the files.
 - Elk: https://wybha-elklandownerallocation2025.tiiny.site
 - Deer: https://wybha-deerlandownertag25.tiiny.site/
 - Antelope:  https://wyantelope-landownerallocation2025.tiiny.site


Consider how these total landowner tag allocations will change if 
1) Tags become transferable, meaning landowners could sell them for thousands of dollars (Senate File 51)
2) Landowners are allotted _no less than_ 40% of tags (Senate File 15)

Conclusion: 
If 40% of tags were automatically allocated to landowners, the public's limited draw opportunity would decline considerably.

## Installation
```
cd /path/to/dir
uv venv ../.venv --python=3.13
source ../.venv/bin/activate
uv pip install -r requirements.txt
```
