FaceFusion
==========

This is a fork of the original [FaceFusion](https://github.com/facefusion/facefusion) project with a modern frontend built with React and Vite.


Preview
-------


Modern Frontend
---------------

This fork includes a new, modern web interface built with React and Shadcn UI.

![Frontend Preview](https://raw.githubusercontent.com/facefusion/facefusion/master/.github/preview.png?sanitize=true)
<!-- TODO: Update with actual screenshot of new frontend -->

### Features
- **Modern UI**: Built with React, Vite, and Shadcn UI.
- **Dark Mode**: Sleek dark theme with "Bai Jamjuree" font.
- **Real-time Updates**: Live terminal logs and progress tracking via WebSocket.
- **Drag & Drop**: Easy file upload for source and target.



Installation
------------

Be aware, the [installation](https://docs.facefusion.io/installation) needs technical skills and is not recommended for beginners. In case you are not comfortable using a terminal, our [Windows Installer](http://windows-installer.facefusion.io) and [macOS Installer](http://macos-installer.facefusion.io) get you started.


Usage
-----

Run the command:

### Standard (Gradio)
```
python facefusion.py [commands] [options]
```

### Modern Frontend (React)
We provide convenient scripts to launch both the backend API and the frontend dev server:

**Windows:**
```batch
run_web.bat
```

**Linux / macOS:**
```bash
./run_web.sh
```


options:
  -h, --help                                      show this help message and exit
  -v, --version                                   show program's version number and exit

commands:
    run                                           run the program
    headless-run                                  run the program in headless mode
    batch-run                                     run the program in batch mode
    force-download                                force automate downloads and exit
    benchmark                                     benchmark the program
    job-list                                      list jobs by status
    job-create                                    create a drafted job
    job-submit                                    submit a drafted job to become a queued job
    job-submit-all                                submit all drafted jobs to become a queued jobs
    job-delete                                    delete a drafted, queued, failed or completed job
    job-delete-all                                delete all drafted, queued, failed and completed jobs
    job-add-step                                  add a step to a drafted job
    job-remix-step                                remix a previous step from a drafted job
    job-insert-step                               insert a step to a drafted job
    job-remove-step                               remove a step from a drafted job
    job-run                                       run a queued job
    job-run-all                                   run all queued jobs
    job-retry                                     retry a failed job
    job-retry-all                                 retry all failed jobs
```



Tech Stack
----------

- **Python**: Core programming language.
- **Gradio**: Web-based user interface.
- **ONNX / ONNX Runtime**: Machine learning model inference.
- **OpenCV**: Computer vision and image processing.
- **NumPy**: Numerical computing.

**Frontend:**
- **React**: UI Library.
- **Vite**: Build tool.
- **Tailwind CSS**: Utility-first CSS framework.
- **Shadcn UI**: Component library.



Project Structure
-----------------

```
facefusion/
├── .github/           # GitHub Actions and templates
├── facefusion/        # Main application package
│   ├── jobs/          # Job management
│   ├── processors/    # Face manipulation processors
│   ├── uis/           # User interface components
│   ├── workflows/     # Workflow definitions
│   └── ...
├── tests/             # Unit and integration tests
├── facefusion.py      # Entry point script
├── install.py         # Installation script
├── requirements.txt   # Python dependencies
├── run.bat            # Windows execution script
├── run_web.bat        # Windows script for Web UI
├── run_web.sh         # Linux/Mac script for Web UI
└── facefusion-web/    # React Frontend
    ├── src/
    ├── package.json
    └── ...

```


Content Censorship
----------------------------

The original Facefusion tried to censor its user with a censorship system that utilized a multi-model ensemble to detect NSFW content. It employed three distinct models:
- **EraX (nsfw_1)**
- **Marqo (nsfw_2)**
- **Freepik (nsfw_3)**
A majority vote logic was applied, where content was flagged only if at least two of the three models agreed on the classification. At NVAI we believe that content moderation should be up to the descretion of the user, not the tool, so naturally this feature has been removed.


Integrity Check (Removed)
-------------------------

The application previously included an internal integrity check that verified the hash of `facefusion/content_analyser.py` on startup. This was intended to prevent unauthorized modifications to the content analysis logic. Having something like this in a non-commercial product is a completely dumb idea. To disable it, remove the hash check in `facefusion/core.py`:

```diff
 def common_pre_check() -> bool:
 	common_modules =\
 	[
 		content_analyser,
 		face_classifier,
 		face_detector,
 		face_landmarker,
 		face_masker,
 		face_recognizer,
 		voice_extractor
 	]
 
-	content_analyser_content = inspect.getsource(content_analyser).encode()
-	content_analyser_hash = hash_helper.create_hash(content_analyser_content)
-
-	return all(module.pre_check() for module in common_modules) and content_analyser_hash == '9b67696d'
+	return all(module.pre_check() for module in common_modules)
```


Documentation
-------------

Read the [documentation](https://docs.facefusion.io) for a deep dive.
