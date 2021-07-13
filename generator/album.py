#!/usr/bin/env python3

import os, sys, shutil, uuid
import pyexiv2, datetime
import json
from PIL import Image, ImageOps
from jinja2 import Template

class RetroAlbum:
    def __init__(self, photoPath):
        self.scriptPath = os.path.dirname(os.path.abspath(__file__))
        self.config = json.load(open(os.path.join(self.scriptPath, 'config.json'), 'r'))
        self.skipDirs = [self.config["albumDir"], self.config["thumbDir"], 'js', 'css', 'default-skin', 'img']
        if photoPath[-1] == '/':
            photoPath = photoPath[:-1]
        self.photoPath = photoPath

    def make_album(self):
        for root, dirs, files in os.walk(self.photoPath, topdown=True, followlinks=True):
            dirName = os.path.basename(root)
            
            if dirName not in self.skipDirs:
                self.parse_dir(root, dirs, files)

    def parse_dir(self, root, dirs, files):
        """ parses a single directory with photos and generates the album """
        folders = []
        images = []
        thumbSizes = []
        albumName = os.path.basename(root)
        print(root, albumName)

        for dirName in dirs:
            if dirName not in self.skipDirs:
                folders.append({'name': dirName})

        for file in files:
            refFile = file.upper()
            if refFile.endswith(tuple(self.config["formats"])):
                image = self.parse_image(root, file)
                thumbSize = image['thumbSize']
                images.append(image)
                if not thumbSize in thumbSizes:
                    thumbSizes.append(thumbSize)

        #print(images)
        #print(thumbSizes)

        #copy needed files
        albumDirPath = os.path.join(root, self.config["albumDir"])
        self.copytree(os.path.join(self.scriptPath, 'base'), albumDirPath)

        templateFile = os.path.join(self.scriptPath, 'templates', 'index.html.j2')
        destFile = os.path.join(root, 'index.html')
        self.template(templateFile, destFile, {'folders': folders, 'images': images, 'albumDir': self.config['albumDir'], 'albumName': albumName} )

        templateFile = os.path.join(self.scriptPath, 'templates', 'album.css.j2')
        destFile = os.path.join(albumDirPath, 'css', 'album.css')
        self.template(templateFile, destFile, {'thumbSizes': thumbSizes, 'size': self.config["thumbSizeSmall"]})

    def parse_image(self, root, file):
        imgPath = os.path.join(root, file)
        albumImgPath = os.path.join(root, self.config["albumDir"], file)
        thumbImgPath = os.path.join(root, self.config["albumDir"], self.config["thumbDir"], file)

        #log('Processing %s to %s and %s' % (imgPath, albumImgPath, thumbImgPath))

        metadata = pyexiv2.metadata.ImageMetadata(imgPath)
        metadata.read()
        
        caption = self.get_exif_tag(metadata, self.config["exif"]["captionKeys"])
        if caption:
            caption = 'data-title="%s"' % caption.value
        else:
            caption = ''
        
        rating = self.get_exif_tag(metadata, self.config["exif"]["ratingKeys"])
        if rating:
            rating = rating.value
        else:
            rating = 0

        dateTime = self.get_exif_tag(metadata, self.config["exif"]["dateKeys"])
        if dateTime:
            dateTime = dateTime.value
        else:
            dateTime = datetime.datetime.today() 

        keywords = self.get_exif_tag(metadata, self.config["exif"]["tagsKeys"])
        if keywords:
            keywords = keywords.value

        #clean metadata
        self.clean_exif(metadata)

        #TODO add custom keys

        #create thumbnail
        if rating >= self.config["ratingLargeThumb"]:
            size = self.config["thumbSizeLarge"]
        else:
            size = self.config["thumbSizeSmall"]
        thumbSize = self.scale_image(imgPath, thumbImgPath, size, metadata)
    

        #create base image
        size = self.config["imageSize"]
        imgSize = self.scale_image(imgPath, albumImgPath, size, metadata)

        return {'dateTime': dateTime, 'file': file, 'caption': caption, 'thumbSize': thumbSize, 'imgSize': imgSize, 'thumbDir': self.config["thumbDir"], 'keywords': keywords, 'rating': rating}

    def get_exif_tag(self, metadata, keys):
        """return first tag from keys or none if nothing found"""
        all_keys = metadata.exif_keys + metadata.iptc_keys + metadata.xmp_keys
        for k in keys:
            if k in all_keys:
                return metadata[k]
        return None

    def scale_image_2(self, imgPath, scaledImgPath, size, metadata):
        size = [size, size]

        dirName = os.path.dirname(scaledImgPath)
        if not os.path.exists(dirName):
            os.makedirs(dirName)

        im = Image.open(imgPath)
        im.thumbnail(size, Image.ANTIALIAS)
        #either this or keep orientation in exif "Exif.Image.Orientation"
        im = ImageOps.exif_transpose(im)
        im.save(scaledImgPath, "JPEG")
        
        if metadata:
            newMetadata = pyexiv2.metadata.ImageMetadata(scaledImgPath)
            newMetadata.read()
            metadata.copy(newMetadata)
            newMetadata.write()

        return im.size

    def scale_image(self, imgPath, scaledImgPath, size, metadata):
        dirName = os.path.dirname(scaledImgPath)
        if not os.path.exists(dirName):
            os.makedirs(dirName)

        im = Image.open(imgPath)
        #either this or keep orientation in exif "Exif.Image.Orientation"
        im = ImageOps.exif_transpose(im)

        newSize = [int(im.width * size / im.height), size]

        #im.thumbnail(size, Image.ANTIALIAS)
        im = im.resize(newSize, Image.LANCZOS)
        im.save(scaledImgPath, "JPEG")
        
        if metadata:
            newMetadata = pyexiv2.metadata.ImageMetadata(scaledImgPath)
            newMetadata.read()
            metadata.copy(newMetadata)
            newMetadata.write()

        return im.size

    def clean_exif(self, metadata):
        """clean metadata"""
        all_keys = metadata.exif_keys + metadata.iptc_keys + metadata.xmp_keys
        keep_keys = self.config['exif']['captionKeys'] + self.config['exif']['ratingKeys'] + self.config['exif']['tagsKeys'] + self.config['exif']['dateKeys'] + self.config['exif']['keepKeys']

        for k in all_keys:
            if k not in keep_keys:
                del metadata[k]

    def copytree(self, src, dst, symlinks=False):
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
                    self.copytree(srcname, dstname, symlinks)
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

    def template(self, templateFile, destFile, data):
        with open(templateFile) as file_:
            template = Template(file_.read())
        open(destFile, 'w').write(template.render(data))

def log(msg):
    print(msg)

if __name__ == "__main__":
    photoPath = sys.argv[1]
    album = RetroAlbum(photoPath)
    album.make_album()

    scriptPath = os.path.dirname(sys.argv[0])
    scriptPath = os.path.abspath(scriptPath)
