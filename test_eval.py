import os,sys
import numpy as np
import pandas as pd
def test_student_submission():
    print("HACKSPHERE 3.0 - Pre-Submission Self-Tester")
    for f in ["predict.py","sample_test_input.csv"]:
        if not os.path.exists(f): print("ERROR: "+f+" not found");sys.exit(1)
    from predict import predict
    data=pd.read_csv("sample_test_input.csv")
    values=predict(data)
    if not isinstance(values,(np.ndarray,list)): print("ERROR: predictions must be ndarray or list");sys.exit(1)
    values=np.asarray(values,dtype=float)
    if len(values)!=len(data): print("ERROR: prediction count mismatch");sys.exit(1)
    if not np.isfinite(values).all(): print("ERROR: NaN or infinite predictions");sys.exit(1)
    print("Valid predictions:",np.round(values[:3],2))
    print("SUCCESS")
if __name__=="__main__": test_student_submission()
