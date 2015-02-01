# Retro Album

This is a one day project which is the result of the need to generate a photo album for my photos at the end of my photo processing workflow. It responds to the following functional needs:

* generate a html photo album using a masonry responsive layout
* understands photo metadata
  * rating metadata: photos with higher ratings have bigger thumbnails
  * date time metadata: photos are sorted by creation date time
  * caption metadata: captions are created from metadata
  * keywords filtering: photos can be filtered using keywords
  * not needed metadata is removed
* can be included in wordpress using a custom plugin using a WordPress shortcode
 

`[retroAlbum album="test"]
This will include in the current post an album which is supposed to be found and $wordpress_site/photos/album

All above functions are implemented in current version 0.0.1.

This project uses:
- [javascript masonry layout library](http://masonry.desandro.com/)
- [lightbox2](http://masonry.desandro.com/)
