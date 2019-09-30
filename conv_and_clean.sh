#!/bin/bash

while getopts ":i:t:o:" opt; do
  case $opt in
    t) t_out="$OPTARG"
    ;;
    i) p_in="$OPTARG"
    ;;
    o) p_out="$OPTARG"
    ;;
    \?) echo "Invalid option -$OPTARG" >&2
    ;;
  esac
done

for filepath in $p_in*.pdf; do
  filename=${filepath##*/}  # Get filename without base path
  filename=${filename%.*}  # Get filename without extension
  output_filename=$p_out$filename
  pdfimages $filepath $output_filename -$t_out # Convert PDF to requested type
  convert $output_filename*.$t_out -rotate -90 $output_filename-%03d.$t_out # rotate all images by 90 degrees anti-clockwise
done
