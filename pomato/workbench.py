# %%
from pathlib import Path
import pandas as pd
import pomato


# %%
# wdir = Path("/examples/") # Change to local copy of examples folder
wdir = Path(r"C:\Users\cw\repositories\MODEZEEN_AP4")
mato = pomato.POMATO(wdir=wdir, options_file="profiles/de_2030.json")
mato.load_data('data_input/DE_2030.zip')

# %% 
# Load already existing results if desired
result_names = ["408_1412_12813_market_results","408_1412_12813_redispatch_DE"]
results_folder = "C:/Users/cw/repositories/MODEZEEN_AP4/data_temp/julia_files/results"
for rn in result_names:
    mato.data.results[rn] = pomato.data.results.Results(mato.data, mato.grid, Path(results_folder+"/"+rn))
    
# %% 

dir(mato.data.results['408_1412_12813_redispatch_DE'])
mato.data.results['408_1412_12813_redispatch_DE'].price()
mato.data.results['408_1412_12813_redispatch_DE'].data.nodes
mato.data.results['408_1412_12813_redispatch_DE'].result_attributes["source_folder"]
str(mato.data.results['408_1412_12813_redispatch_DE'].data.wdir)


res_split = '408_1412_12813_redispatch_DE'.split('_')
res_name = '_'.join(res_split[:3])

# %%
mato.data.results['408_1412_12813_redispatch_DE'].export_dieter_prosumage()
