import unittest
import sys
import os

# Add current directory to path so imports work
sys.path.append(os.getcwd())

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.discover(".")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())
