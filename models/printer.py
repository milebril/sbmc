import numpy as np
import torch as th
import matplotlib.pyplot as plt

from sbmc import modules

import ttools

# xvals = np.arange(0, 30)
# print(xvals)

# yvals =[0.5726340413093567, 0.5141341734773006,0.4683532755094161, 0.39301591646821626, 0.31967072069574165,0.26262103684601085,0.21824635701880418,0.18373067618579222,0.15688333866050466,0.13600069293735617,0.11975723935083143,0.10712221038310639,0.09729370313634868,0.08964749593412953,0.08369752371714696,0.07906295711795788,0.07543064419607469,0.07232814933692731,0.06953041894341742,0.0671772554661873,0.06402639109063135,0.06089985079456816,0.05788817700835923,0.055004844207548406,0.052333140987446986,0.049997469333577765,0.048019502384442254,0.04634857640542268,0.04493516124339736,0.0437463957017719]

# plt.plot(xvals, yvals)
# plt.title("Loss ")
# plt.show()
path = "epoch_1"

temp = th.load(f"/home/emil/Documents/Temporal-SBMC-extension/output/emil/training_sbmc_theirs/epoch_1.pth", map_location=th.device('cpu'))
open(f'models/{path}.txt', 'w').close()
f = open(f'models/{path}.txt', "a")
f.write(str(temp['model']))
f.close()