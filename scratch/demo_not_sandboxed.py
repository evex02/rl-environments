from run_code import run_python

print("demo started")
ok, out = run_python("import os; print(os.listdir('.'))")
print("finished OK:", ok)
print(out)