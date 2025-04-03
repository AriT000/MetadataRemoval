from bottle import route, run, request, response, static_file
import os
import subprocess
import uuid
import tempfile
import shutil

# Create upload directory if it doesn't exist
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "pdf_uploads")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Check for required dependencies
def check_dependencies():
    dependencies = {
        'pdftk': False,
        'exiftool': False,
        'qpdf': False,
        'pdfinfo': False
    }
    
    for cmd in dependencies.keys():
        if shutil.which(cmd):
            dependencies[cmd] = True
    
    return dependencies

# Verify dependencies at startup
DEPENDENCIES = check_dependencies()

@route("/")
def index():
    # Check for missing dependencies
    missing = [cmd for cmd, installed in DEPENDENCIES.items() if not installed]
    
    page = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>File Metadata Remover</title>
        <style>
            body {{ 
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            .upload-form {{
                border: 2px dashed #ccc;
                padding: 20px;
                text-align: center;
                margin: 20px 0;
                border-radius: 5px;
            }}
            .btn {{
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                cursor: pointer;
                margin-top: 10px;
                border-radius: 4px;
            }}
            .btn:hover {{
                background-color: #45a049;
            }}
            .warning {{
                background-color: #f8d7da; 
                color: #721c24; 
                padding: 10px; 
                border: 1px solid #f5c6cb; 
                border-radius: 4px; 
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <h1>File Metadata Remover</h1>
        <p>Upload a PDF file to remove all metadata.</p>
        
        {f'<div class="warning"><strong>Warning:</strong> The following required tools are missing: {", ".join(missing)}. Please install them to use this application.</div>' if missing else ''}
        
        <div class="upload-form">
            <form action="/upload" method="post" enctype="multipart/form-data" {('disabled' if missing else '')}>
                <input type="file" name="upload" accept=".pdf" required {('disabled' if missing else '')}>
                <br>
                <button type="submit" class="btn" {('disabled' if missing else '')}>Clean and Download</button>
            </form>
        </div>
        
        <div>
            <h3>What this tool does:</h3>
            <ul>
                <li>Removes PDF document information (author, creation date, etc.)</li>
                <li>Strips EXIF metadata</li>
                <li>Removes embedded metadata</li>
                <li>Linearizes the PDF for web optimization</li>
            </ul>
        </div>
    </body>
    </html>
    """
    return page

@route("/upload", method="POST")
def upload():
    # Check for missing dependencies
    missing = [cmd for cmd, installed in DEPENDENCIES.items() if not installed]
    if missing:
        return f"Error: Missing required tools: {', '.join(missing)}. Please install them to use this application."
    
    upload = request.files.get("upload")
    
    if not upload:
        return "No file uploaded"
    
    if not upload.filename.lower().endswith('.pdf'):
        return "Only PDF files are supported at this time"
    
    # Generate a unique filename to avoid conflicts
    file_id = str(uuid.uuid4())
    original_filename = upload.filename
    temp_filename = f"{file_id}.pdf"
    final_path = os.path.join(UPLOAD_DIR, temp_filename)
    
    # Save the uploaded file
    upload.save(final_path)
    
    try:
        # Create a shell script with our commands
        script_path = os.path.join(UPLOAD_DIR, f"{file_id}.sh")
        with open(script_path, 'w') as script:
            script.write(f'''#!/bin/bash
                        set -e  # Exit immediately if a command fails
                        set -x  # Print commands before execution for debugging

                        cd "{UPLOAD_DIR}"
                        input_file="{temp_filename}"

                        # Check if tools are available
                        echo "Checking dependencies..."
                        which pdftk || echo "pdftk not found"
                        which exiftool || echo "exiftool not found"
                        which qpdf || echo "qpdf not found"
                        which sed || echo "sed not found"
                        which pdfinfo || echo "pdfinfo not found"

                        # Check if input file exists
                        echo "Checking input file..."
                        ls -l "$input_file"

                        # Step 1: Remove PDF metadata
                        echo "Step 1: Removing PDF metadata..."
                        pdftk "$input_file" dump_data > "{file_id}-original-metadata.txt" || echo "Error in dumping data"
                        cat "{file_id}-original-metadata.txt" | sed -e 's/\\(InfoValue:\\)\\s.*/\\1 /g' > "{file_id}-modified-metadata.txt" || echo "Error in sed command"
                        pdftk "$input_file" update_info "{file_id}-modified-metadata.txt" output "clean-$input_file" || echo "Error in updating info"

                        # Step 2: Remove EXIF and embedded metadata
                        echo "Step 2: Removing EXIF metadata..."
                        exiftool -all:all= "clean-$input_file" || echo "Error in exiftool command 1"
                        exiftool -all:all "clean-$input_file" || echo "Error in exiftool command 2"
                        exiftool -extractEmbedded -all:all "clean-$input_file" || echo "Error in exiftool command 3"

                        # Step 3: Linearize PDF
                        echo "Step 3: Linearizing PDF..."
                        qpdf --linearize "clean-$input_file" "clean2-$input_file" || echo "Error in qpdf command"

                        # Step 4: Verify clean state (for debugging purposes)
                        echo "Step 4: Verifying clean state..."
                        pdftk "clean2-$input_file" dump_data > "{file_id}-verification.txt" || echo "Error in final dump_data"
                        exiftool "clean2-$input_file" >> "{file_id}-verification.txt" || echo "Error in final exiftool"
                        pdfinfo -meta "clean2-$input_file" >> "{file_id}-verification.txt" || echo "Error in final pdfinfo"

                        # Move the final cleaned file back to original name
                        echo "Step 5: Finalizing..."
                        mv "clean2-$input_file" "$input_file" || echo "Error in mv command"
                        rm -f "clean-$input_file" || echo "Error in rm command"
                        rm -f "{file_id}-original-metadata.txt" "{file_id}-modified-metadata.txt" || echo "Error in cleanup"

                        echo "Process completed successfully"
                        ''')
        
        # Make the script executable
        os.chmod(script_path, 0o755)
        
        # Run the script with output capturing
        result = subprocess.run(
            ['/bin/bash', script_path], 
            check=False,  # Don't raise exception yet
            capture_output=True,
            text=True
        )
        
        # Check if the script failed
        if result.returncode != 0:
            # Keep the script for debugging
            with open(os.path.join(UPLOAD_DIR, f"{file_id}-error-log.txt"), 'w') as error_log:
                error_log.write("STDOUT:\n")
                error_log.write(result.stdout)
                error_log.write("\n\nSTDERR:\n")
                error_log.write(result.stderr)
                error_log.write("\n\nSCRIPT CONTENT:\n")
                with open(script_path, 'r') as script_file:
                    error_log.write(script_file.read())
            
            error_log_path = os.path.join(UPLOAD_DIR, f"{file_id}-error-log.txt")
            return f"""
            <html>
            <head>
                <title>Error Processing File</title>
                <style>
                    body {{ 
                        font-family: Arial, sans-serif;
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .error {{
                        background-color: #f8d7da;
                        color: #721c24;
                        padding: 15px;
                        border-radius: 5px;
                        margin: 20px 0;
                    }}
                    pre {{
                        background-color: #f8f9fa;
                        padding: 15px;
                        border-radius: 5px;
                        overflow-x: auto;
                    }}
                </style>
            </head>
            <body>
                <h1>Error Processing File</h1>
                <div class="error">
                    <p>There was an error processing your file. The error log is available at: <code>{error_log_path}</code></p>
                </div>
                <h2>Error Details</h2>
                <h3>Standard Output</h3>
                <pre>{result.stdout}</pre>
                <h3>Standard Error</h3>
                <pre>{result.stderr}</pre>
                <p><a href="/">Go back to homepage</a></p>
            </body>
            </html>
            """
                
        # Clean up the script if successful
        os.unlink(script_path)
        
        # Set up response for file download
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="cleaned_{original_filename}"'
        
        # Return the cleaned file and set it to be deleted after sending
        return static_file(temp_filename, root=UPLOAD_DIR, download=f"cleaned_{original_filename}")
    
    except subprocess.CalledProcessError as e:
        return f"Error processing file: {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"
    finally:
        # Clean up verification file if it exists
        verification_file = os.path.join(UPLOAD_DIR, f"{file_id}-verification.txt")
        if os.path.exists(verification_file):
            try:
                os.unlink(verification_file)
            except:
                pass

if __name__ == "__main__":
    print(f"Server running at http://127.0.0.1:8080")
    print(f"Files will be temporarily stored in: {UPLOAD_DIR}")
    print("Required dependencies status:")
    for cmd, installed in DEPENDENCIES.items():
        print(f"- {cmd}: {'Installed' if installed else 'Missing'}")
    run(host="127.0.0.1", port=8080, debug=True)