<?php
/**
 * Plugin Name: Retro Album
 * Plugin URI: http://www.len.ro
 * Description: This plugin includes Retro Albums in WP
 * Version: 0.0.1
 * Author: Len
 * Author URI: http://www.len.ro
 * License: MIT
 */

// Register style sheet.
add_action( 'wp_enqueue_scripts', 'register_plugin_styles' );

/**
 * Register style sheet.
 */
function register_plugin_styles() {
  wp_register_style( 'retro-album-album', plugins_url( 'retro-album/css/album.css' ) );
  wp_enqueue_style( 'retro-album-album' );

  wp_register_style( 'retro-album-lightbox', plugins_url( 'retro-album/css/lightbox.css' ) );
  wp_enqueue_style( 'retro-album-lightbox' );

  wp_register_script('imagesloaded', plugins_url('retro-album/js/imagesloaded.pkgd.min.js'), array('jquery'), '3.1.8', false);
  wp_enqueue_script('imagesloaded');

  wp_register_script('masonry', plugins_url('retro-album/js/masonry.pkgd.min.js'), array('jquery'), '3.2.2', false);
  wp_enqueue_script('masonry');

  wp_register_script('lightbox', plugins_url('retro-album/js/lightbox.min.js'), array('jquery'), '2.7.1', false);
  wp_enqueue_script('lightbox');
}

// [retroalbum album="paradis"]
function retroalbum_func($atts) {
  $a = shortcode_atts( array(
			     'album' => '',
			     'uri' => '',
			     ), $atts );
  $album = $a['album'];
  if (!empty($album)){
    $albumpath = '/photos/' . $album;
    $baseurl = get_site_url() . $albumpath;
    $path = str_replace('/wp-content/themes', '', get_theme_root()) . $albumpath . '/album.inc';
    return str_replace('$BASE', $baseurl, file_get_contents($path));
  }else{
    return '';
  }
  //return wp_remote_fopen($url);
}

add_shortcode('retroalbum', 'retroalbum_func');