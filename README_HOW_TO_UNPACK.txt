========================================================================
 AI TRANSLATOR 2 CHEAP - HOW TO UNPACK & RESTORE THE PROJECT
========================================================================

WHY WERE FILE EXTENSIONS CHANGED?
---------------------------------
Email services (such as Gmail, Outlook, Yahoo, etc.) automatically block 
attachments containing executable script files (.bat, .vbs, .js) for security 
reasons, even when packaged inside standard ZIP archives.

To make this project 100% email-safe and sendable, executable script files 
have been given a temporary ".txt" extension:
  - "AI Translator 2 Codex Cheap.bat"  -->  "AI Translator 2 Codex Cheap.bat.txt"
  - "launcher.vbs"                     -->  "launcher.vbs.txt"
  - "app.js"                           -->  "app.js.txt"
  - "engine-info.js"                   -->  "engine-info.js.txt"
  - "telemetry.js"                     -->  "telemetry.js.txt"

------------------------------------------------------------------------
STEP-BY-STEP UNPACKING INSTRUCTIONS
------------------------------------------------------------------------

STEP 1: Unpack / Extract the Archive
------------------------------------
1. If the file you received is named "AI_Translator_2_Cheap_Email_Package.zip.txt",
   rename it to "AI_Translator_2_Cheap_Email_Package.zip" first.
2. Extract (unzip) the file contents into a folder on your computer.


STEP 2: Restore File Extensions
-------------------------------

--- METHOD 1: AUTOMATIC 1-CLICK RESTORATION (RECOMMENDED) ---
1. Open PowerShell inside the extracted project folder:
   - Right-click empty space in the folder -> Select "Open in Terminal" or "Open PowerShell here".
2. Copy and paste the following single command line and press Enter:

Get-ChildItem -Recurse -Filter "*.txt" | Where-Object { $_.Name -match '\.(bat|vbs|js)\.txt$' } | Rename-Item -NewName { $_.Name -replace '\.txt$', '' }

All script extensions will be restored instantly!


--- METHOD 2: MANUAL RESTORATION ---
If you prefer to rename files manually in File Explorer:

1. In the main root folder:
   - Rename:  AI Translator 2 Codex Cheap.bat.txt   -->   AI Translator 2 Codex Cheap.bat
   - Rename:  launcher.vbs.txt                      -->   launcher.vbs

2. In the "static" folder:
   - Rename:  app.js.txt                            -->   app.js

3. In the "static/js/modules" folder:
   - Rename:  engine-info.js.txt                    -->   engine-info.js
   - Rename:  telemetry.js.txt                      -->   telemetry.js

(Note: If Windows hides file extensions, enable "File name extensions" under the "View" tab in File Explorer before renaming).

------------------------------------------------------------------------
STEP 3: Run the Application
---------------------------
Once extensions are restored, run either:
  - "launcher.vbs" (Silent start)
  - "AI Translator 2 Codex Cheap.bat" (Console start)
========================================================================
