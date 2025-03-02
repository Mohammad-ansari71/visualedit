# Visual Edit

A Python-based GUI tool for image annotation and processing, with support for YOLO format labels.

## Features

- Image viewing and navigation
- YOLO format annotation support
- Label format conversion (YOLO, COCO, JSON)
- Smart crop functionality with annotation preservation
- Batch processing capabilities
- Real-time annotation information display
- Zoom and pan controls
- Resizable and adjustable interface with horizontal panel dividers
- Optimized image rendering for improved performance
- Enhanced zoom functionality with smooth scaling
- Improved image loading with caching for better performance

## Requirements

- Python 3.6+
- OpenCV (cv2)
- Pillow (PIL)
- tkinter
- PyYAML

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/visualedit.git
cd visualedit
```

2. Install dependencies:
```bash
pip install opencv-python pillow pyyaml
```

3. Create required directories:
```bash
mkdir images labels label_format
```

4. Create a `data.yaml` file with your class names:
```yaml
names:
  0: class1
  1: class2
  # Add more classes as needed
```

## Usage

Run the application:
```bash
python visualedit.py
```

### Main Features

1. **Label Converter**
   - Convert between different label formats (YOLO, COCO, JSON)
   - Preserve original image sizes
   - Batch conversion support

2. **Smart Crop**
   - Crop images while preserving annotations
   - Choose between centered or random cropping
   - Set safe margins and output resolution
   - Batch processing support

3. **Image Navigation**
   - Browse through images in a directory
   - View and edit annotations
   - Real-time information display
   - Zoom and pan controls
   - Optimized rendering for faster navigation

4. **Enhanced User Interface**
   - Horizontally adjustable panels for flexible workspace layout
   - Organized control buttons at the top of the window
   - Improved image display with zoom level persistence between images
   - Efficient image caching for better performance
   - Smooth mousewheel scrolling functionality

## Directory Structure

```
visualedit/
├── visualedit.py     # Main application
├── data.yaml         # Class definitions
├── images/          # Image directory
├── labels/          # YOLO format labels
└── label_format/    # Other label formats
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

Project maintainer: massimilian.menghin@gmail.com 