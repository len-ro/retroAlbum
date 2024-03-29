#!/usr/bin/env python3

import os, sys, shutil, uuid
import pyexiv2, datetime
from PIL import Image, ImageOps

formats = ('JPG', 'JPEG')
thumbsDir = 'thumbs'
skipDirs = (thumbsDir, 'img')

smallThumbSize = (160, 160)
thumbOffset = 13 # 2*margin + gutter = 2*4 + 5

"""exifKeys to identify caption"""
exifCaptionKeys = ['Exif.Image.ImageDescription', 'Iptc.Application2.Caption']

"""exifKeys to identify rating"""
exifRatingKeys = ['Xmp.xmp.Rating']

"""exifKeys to identify tags"""
exifTagsKeys = ['Xmp.dc.subject', 'Iptc.Application2.Keywords']

"""exifKeys to identify datetime"""
exifDateKeys = ['Exif.Photo.DateTimeOriginal']

"""Preserve these keys in exif, the rest will be removed"""
exifKeepKeys = ['Exif.Image.Artist', 'Exif.Image.Copyright', 'Iptc.Application2.Copyright', 'Xmp.dc.creator']


def thumbSimple(basePath, thumbPath, rating):
    ratio = float(100 + 20 * rating)/100
    thumbSize = [int(ratio * x) for x in smallThumbSize]

    im = Image.open(basePath)
    im.thumbnail(thumbSize, Image.ANTIALIAS)
    im.save(thumbPath, "JPEG")
    
    return im.size

def thumbSquare(basePath, thumbPath, rating):
    thumbSize = smallThumbSize
    if rating >= 2:
        thumbSize = [2*x + thumbOffset for x in thumbSize]
    im = Image.open(basePath)
    
    ratio = float(im.size[0]) / im.size[1]

    if ratio > 1:
        thumbSizeX = (int(ratio * thumbSize[0]), thumbSize[1])
    else:
        thumbSizeX = (thumbSize[0], int(1 / ratio * thumbSize[1]))

    #im.thumbnail(thumbSizeX, Image.ANTIALIAS)
    #im = im.crop((0, 0, thumbSize[1], thumbSize[0]))
    im = ImageOps.fit(im, thumbSize, Image.ANTIALIAS)
    im.save(thumbPath, "JPEG")

    #print im.size, ratio, thumbSizeX, thumbSize
    return im.size

thumb = thumbSquare

templates = {
    'index':{'name':'index', 'oFile':'index.html', 'excludeKeys':['private']}, 
    'wp':{'name':'wp', 'oFile':'album.inc', 'excludeKeys':['private']},
    'private':{'name':'index', 'oFile':'%s.html' % (str(uuid.uuid4())[-8:])}
}

def init_templates(basePath):
    for k in templates:
        templates[k]['basePath'] = basePath
        update_template(k, 'header', None, False)

def update_templates(part, data, cache, filter = False):
    for k in templates:
        update_template(k, part, data, cache, filter)

def write_templates(albumPath):
    """writes all templates to disk"""
    for k in templates:
        template = templates[k]
        oPath = os.path.join(albumPath, template['oFile'])
        log('Generating %s' % oPath)
        open(oPath, 'w').write(template['output'])

def update_template(name, part, data, cache, filter = False):
    template = templates[name]

    if filter and 'excludeKeys' in template and 'keywords' in data:
        for xk in template['excludeKeys']:
            if data['keywords'] and xk in data['keywords']:
                #log('Skip %s' % data)
                return

    if cache and 'cache.%s' % part in template:
        output = template['cache.%s' % part]
    else:
        tPath = os.path.join(template['basePath'], '%s.%s' % (template['name'], part))
        output = open(tPath).read()

    if data:
        output = output % data

    if 'output' not in template:
        template['output'] = output
    else:
        template['output'] = template['output'] + output

def get_exif_tag(metadata, keys):
    """return first tag from keys or none if nothing found"""
    all_keys = metadata.exif_keys + metadata.iptc_keys + metadata.xmp_keys
    for k in keys:
        if k in all_keys:
            return metadata[k]
    return None

def clean_exif(metadata):
    """clean metadata"""
    all_keys = metadata.exif_keys + metadata.iptc_keys + metadata.xmp_keys
    keep_keys = exifCaptionKeys + exifRatingKeys + exifTagsKeys + exifDateKeys + exifKeepKeys

    for k in all_keys:
        if k not in keep_keys:
            del metadata[k]

    metadata.write()

def parse(dir):
    for root, dirs, files in os.walk(dir, topdown=False, followlinks=True):
        if root.endswith(skipDirs):
            continue

        #create thumbs dir
        _thumbsDir = os.path.join(root, thumbsDir)
        if not os.path.exists(_thumbsDir):
            os.makedirs(_thumbsDir)

        images = []

        for file in files:
            refFile = file.upper()
            if refFile.endswith(formats):
                fullPath = os.path.join(root, file)
                thumbPath = os.path.join(root, thumbsDir, file)

                log('Processing %s to %s' % (fullPath, thumbPath))

                metadata = pyexiv2.metadata.ImageMetadata(fullPath)
                metadata.read()
                
                caption = get_exif_tag(metadata, exifCaptionKeys)
                if caption:
                    caption = 'data-title="%s"' % caption.value
                else:
                    caption = ''
                
                rating = get_exif_tag(metadata, exifRatingKeys)
                if rating:
                    rating = rating.value
                else:
                    rating = 0

                dateTime = get_exif_tag(metadata, exifDateKeys)
                if dateTime:
                    dateTime = dateTime.value
                else:
                    dateTime = datetime.datetime.today() 

                keywords = get_exif_tag(metadata, exifTagsKeys)
                if keywords:
                    keywords = keywords.value

                clean_exif(metadata)

                size = thumb(fullPath, thumbPath, rating)

                imageData = {'dateTime': dateTime, 'file': file, 'caption': caption, 'w': size[0], 'h': size[1], 'thumbsDir': thumbsDir, 'keywords': keywords}
                images.append(imageData)

        for image in sorted(images, key=lambda i: i['dateTime']):
            update_templates('line', image, True, filter = True)

def copytree(src, dst, symlinks=False):
    """Reimplementation of shutil.copytree to allow existing directories to be used"""
    names = os.listdir(src)

    if not os.path.isdir(dst):
        os.makedirs(dst)

    errors = []
    for name in names:
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                copytree(srcname, dstname, symlinks)
            else:
                shutil.copy2(srcname, dstname)
            # XXX What about devices, sockets etc.?
        except (IOError, os.error) as why:
            errors.append((srcname, dstname, str(why)))
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except IOError as err:
            errors.extend(err.args[0])
    try:
        shutil.copystat(src, dst)
    except WindowsError:
        # can't copy file access times on Windows
        pass
    except OSError as why:
        errors.extend((src, dst, str(why)))
    if errors:
        raise IOError(errors)

def init_dir(basePath, albumPath):
    import shutil
    log('Initializing album path %s from %s' % (albumPath, basePath))
    copytree(basePath, albumPath)

def log(msg):
    print(msg)

if __name__ == "__main__":
    albumPath = sys.argv[1]

    scriptPath = os.path.dirname(sys.argv[0])
    scriptPath = os.path.abspath(scriptPath)

    """copies required files"""
    init_dir(os.path.join(scriptPath, 'base'), albumPath)

    """sets templates path"""
    init_templates(os.path.join(scriptPath, 'templates'))
    
    """parse dir and creates album"""
    parse(albumPath)

    update_templates('footer', None, False)
    write_templates(albumPath)



