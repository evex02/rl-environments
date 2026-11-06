from run_code import run_python

ok, out = run_python("import os; print(os.listdir('.'))")
print(out)