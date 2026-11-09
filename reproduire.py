from pathlib import Path
import subprocess,sys
root=Path(__file__).resolve().parent
subprocess.run([sys.executable,str(root/'03_ANALYSE/analyse.py')],check=True)
subprocess.run([sys.executable,str(root/'04_LATEX/compiler.py')],check=True)
