example_separator = "\n\n\n"


export PYTHON_PATH=$(PWD)/src

python examples/delay-print.py

echo "\n"
echo "\n"
echo "\n"
python examples/delay-print-queue-item-object.py

echo "\n"
echo "\n"
echo "\n"
python examples/delay-print-async.py

echo "\n"
echo "\n"
echo "\n"
python examples/delay-print-more-params.py

echo "\n"
echo "\n"
echo "\n"
python examples/delay-print-on-close-thread.py

echo "\n"
echo "\n"
echo "\n"
echo "========================================================"

echo "\n"
echo "\n"
echo "\n"
python examples/delay-print-file-logging.py

echo "\n"
echo "\n"
echo "\n"
python examples/delay-print-log-level.py
