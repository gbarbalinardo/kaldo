from kaldo.forceconstants import ForceConstants
import numpy as np
from kaldo.phonons import Phonons
from kaldo.conductivity import Conductivity

forceconstants = ForceConstants.from_folder('hiphive_si_bulk', supercell=[3, 3, 3],format='hiphive')
k = 5
phonons_config = {'kpts': [k, k, k],
                  'is_classic': False,
                  'temperature': 300,
                  'folder':'ald',
                  'is_tf_backend':False,
                  'storage':'numpy'}
phonons = Phonons(forceconstants=forceconstants, **phonons_config)

print('\n')
rta_cond_matrix = Conductivity(phonons=phonons, method='rta').conductivity.sum(axis=0)
print('Rta conductivity (W/mK): %.3f'%(np.mean(np.diag(rta_cond_matrix))))
print(rta_cond_matrix)

print('\n')
sc_cond_matrix = Conductivity(phonons=phonons, method='sc',n_iterations=20).conductivity.sum(axis=0)
print('Self-consistent conductivity (W/mK): %.3f'%(np.mean(np.diag(sc_cond_matrix))))
print(sc_cond_matrix)

print('\n')
qhgk_cond_matrix = Conductivity(phonons=phonons, method='qhgk').conductivity.sum(axis=0)
print('Qhgk conductivity (W/mK): %.3f'%(np.mean(np.diag(qhgk_cond_matrix))))
print(qhgk_cond_matrix)

print('\n')
inv_cond_matrix = (Conductivity(phonons=phonons, method='inverse').conductivity.sum(axis=0))
print('Inverse conductivity (W/mK): %.3f'%(np.mean(np.diag(inv_cond_matrix))))
print(inv_cond_matrix)
