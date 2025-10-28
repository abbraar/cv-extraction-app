# CV Information Extractor with Gemini API

This tool extracts structured information from CVs using Google's Gemini AI. It can process text files and provides a clean JSON output with the extracted information.

## Prerequisites

- Python 3.8 or higher
- Gemini API key from [Google AI Studio](https://makersuite.google.com/)

## Setup

1. Clone this repository or download the files
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file and add your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

## Usage

### Basic Usage

```bash
python cv_processor.py path/to/your/cv.txt -o output.json
```

### Arguments

- `cv_file`: Path to the CV file (required)
- `-o, --output`: Output JSON file path (default: output.json)

### Example

```bash
python cv_processor.py example_cv.txt -o candidate_info.json
```

## Output Format

The tool extracts the following information:

- Full name
- Contact information (email, phone)
- Education history
- Work experience
- Skills
- Languages
- Professional summary

## Notes

- The tool works best with well-formatted text files
- For PDF or DOCX files, you may need to install additional dependencies
- The quality of extraction depends on the Gemini API's capabilities and the input format

## License

This project is open source and available under the MIT License.
