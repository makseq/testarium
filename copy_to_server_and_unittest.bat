hg commit -m CopyToServer
setup.py sdist
xcopy dist\testarium-0.1.zip \\server\makseq\#sites\testarium.makseq.com /Y
cd unittests
python general_test.py full
cd ..
