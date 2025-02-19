Install on Windows 10/11:
1: Install Anaconda
2: Install git for Windows (https://gitforwindows.org/) - Requires restart
3: Open anaconda_prompt
4: Clone axivity-pp repository: git clone https://github.com/AtleSkjelbred/axivity-pp.git
5: Navigate to folder: cd axivity-pp
6: Create environment: conda create --name axivity python=3.9 --no-default-packages -y
7: Activate environment: conda activate axivity
8: Install packages: pip install -r requirements.txt

Get started
In terminal, nagivate to the folder: cd axivity-pp
If there are updates for the framework: git pull origin main
Activate environment: activate axivity
Run the program: python main.py --data-folder <Path to data> (NB: end with /)
Running the program without --data-folder command defaults to folder "data" in axivity-pp