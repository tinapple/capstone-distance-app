# MediaPipe Body Distance Tracker

A simple application that tracks a person's distance from the camera using computer vision. The app uses MediaPipe for body pose detection and sends the distance data via OSC (Open Sound Control).

## Features

- Real-time body pose tracking
- Distance estimation using torso and head points
- OSC output for distance values
- Visual feedback with color-coded distance bar
- Mode switching between face and body tracking
- Smooth filtering of distance values

## Installation

### Option 1: Running from Source (Python)

1. Install Python 3.10 or later
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python pose_to_osc.py
   ```

### Option 2: Windows Executable

1. Download the latest release from the [Releases](https://github.com/tinapple/capstone-distance-app/releases) page
2. Extract and run `MediaPipe_Body_Tracker.exe`

## Building the Executable

To create your own Windows executable:

1. Install Python and dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Build using PyInstaller:
   ```bash
   pyinstaller pose_to_osc.spec
   ```
3. Find the executable in the `dist` folder

## Usage

1. Launch the application
2. Allow camera access when prompted
3. Stand in view of the camera
4. The app will display:
   - Body pose skeleton
   - Yellow bounding box showing tracked area
   - Distance measurement in pixels
   - Color-coded distance bar

### Controls
- Press 'm' to switch between face and body tracking modes
- Press 'q' to quit

### OSC Output
The app sends OSC messages to:
- Address: `localhost`
- Port: `8000`
- Message format: `/body/distance [value]`

## Development

### Files
- `pose_to_osc.py`: Main application code
- `requirements.txt`: Python dependencies
- `pose_to_osc.spec`: PyInstaller specification for creating executables

### Dependencies
- MediaPipe: For body pose detection
- OpenCV: For camera capture and display
- Python-OSC: For sending OSC messages
- NumPy: For numerical operations

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
