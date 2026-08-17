# Atlas — Gemini Research Studio

Atlas is a real desktop research workspace powered by the Gemini API and built with PyQt6. It is not a search mock-up: it calls Gemini's Interactions API, uses Google Search grounding and URL context, accepts local media and documents, and can write model-generated project files to your Downloads folder.

## What it does

- Researches a question with Gemini + Google Search grounding and lists the returned source citations.
- Lets you give one or more public URLs for focused URL-context research.
- Analyses local images, video, audio, PDFs, Word documents, PowerPoint files, text files, and source code with Gemini's Files API.
- Builds a complete starter project from a prompt. Atlas asks Gemini for validated JSON, checks every returned path, and writes the project beneath your Downloads folder.
- Repairs an existing code project from its full error report and an optional screenshot. Atlas supplies Gemini with the readable source/configuration files, validates every proposed changed path, and saves original changed files under `.atlas-backups` before applying a repair.
- Lets you use the current supported Flash models, refresh the models available to your Gemini API key, or enter a model name manually.

## Set up

1. Install Python 3.11 or newer.
2. Open a terminal in this folder and install the dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Create a Gemini API key in [Google AI Studio](https://aistudio.google.com/app/apikey).
4. Start the app:

   ```powershell
   python app.py
   ```

5. Open **Settings** in Atlas, paste the API key, and choose **Save key**. You can instead set the `GEMINI_API_KEY` environment variable before starting the app.

## Important notes

- Search grounding returns the sources Gemini used. It cannot enumerate every page, image, or video indexed by Google, and source availability changes over time.
- Atlas shows returned citations as clickable web, image-page, or video-page links. Image Search itself is only enabled by Google for specific image-capable Gemini models; standard Flash research still finds and cites relevant web pages.
- The Gemini API, model availability, quotas, geographic availability, and billing are controlled by Google and by your API key. Atlas does not contain a key or bypass those controls.
- Model-generated code should always be reviewed and run in an isolated environment before use. Atlas prevents absolute and parent-directory paths when writing a generated project, so it only creates files inside the selected project directory.
- Project repair omits dependency/build folders, existing backups, files larger than 256 KB, and extra source after 250 files or 2 MB. Atlas tells you when that limit excludes files, so you can reduce the project scope or supply a more specific error.
- Your API key is stored locally using the operating system's Qt settings store if you choose **Save key**. Use `GEMINI_API_KEY` instead if you do not want it saved by the app.

## Project structure

```text
app.py                         Application entry point
atlas/
  gemini_service.py            Gemini Interactions and Files API integration
  project_writer.py             JSON validation and safe project creation
  settings.py                   Local user settings
  workers.py                    Non-blocking UI tasks
  ui.py                         PyQt6 interface
tests/                          Offline tests for project validation
```
