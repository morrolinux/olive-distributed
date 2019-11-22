#!/usr/bin/env python3

from xml.dom import minidom
xmldoc = minidom.parse('0.1-video.ove')
itemlist = xmldoc.getElementsByTagName('clip')
num_clips = len(itemlist)
print("Number of clips: ", num_clips)

m = max(int(v.attributes['out'].value) for v in itemlist[max(0,num_clips-50):num_clips])

print("Project len:", m)
