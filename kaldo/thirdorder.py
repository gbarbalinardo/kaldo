from kaldo.forceconstant import ForceConstant

from ase import Atoms
import os
import ase.io
import numpy as np
from scipy.sparse import load_npz
from sparse import COO
from kaldo.interface.eskm_io import import_from_files
import kaldo.interface.shengbte_io as shengbte_io
import ase.units as units
from kaldo.helpers.logger import get_logger
logging = get_logger()

REPLICATED_ATOMS_FILE = 'replicated_atoms.xyz'
THIRD_ORDER_FILE_SPARSE = 'third.npz'
THIRD_ORDER_FILE = 'third.npy'

class ThirdOrder(ForceConstant):

    @classmethod
    def load(cls, folder, supercell=(1, 1, 1), format='eskm', third_energy_threshold=0.):
        """
        Create a finite difference object from a folder
        :param folder:
        :param supercell:
        :param format:
        :param third_energy_threshold:
        :param is_acoustic_sum:
        :return:
        """
        if format == 'numpy':

            if folder[-1] != '/':
                folder = folder + '/'
            config_file = folder + REPLICATED_ATOMS_FILE
            replicated_atoms = ase.io.read(config_file, format='extxyz')

            n_replicas = np.prod(supercell)
            n_total_atoms = replicated_atoms.positions.shape[0]
            n_unit_atoms = int(n_total_atoms / n_replicas)
            unit_symbols = []
            unit_positions = []
            for i in range(n_unit_atoms):
                unit_symbols.append(replicated_atoms.get_chemical_symbols()[i])
                unit_positions.append(replicated_atoms.positions[i])
            unit_cell = replicated_atoms.cell / supercell

            atoms = Atoms(unit_symbols,
                          positions=unit_positions,
                          cell=unit_cell,
                          pbc=[1, 1, 1])

            _third_order = COO.from_scipy_sparse(load_npz(folder + THIRD_ORDER_FILE_SPARSE)) \
                .reshape((n_unit_atoms * 3, n_replicas * n_unit_atoms * 3, n_replicas * n_unit_atoms * 3))
            third_order = ThirdOrder(atoms, replicated_atoms.positions, supercell, _third_order)

        elif format == 'eskm':
            config_file = str(folder) + "/CONFIG"
            third_file = str(folder) + "/THIRD"

            replicated_atoms = ase.io.read(config_file, format='dlp4')
            n_replicas = np.prod(supercell)
            n_total_atoms = replicated_atoms.positions.shape[0]
            n_unit_atoms = int(n_total_atoms / n_replicas)
            unit_symbols = []
            unit_positions = []
            for i in range(n_unit_atoms):
                unit_symbols.append(replicated_atoms.get_chemical_symbols()[i])
                unit_positions.append(replicated_atoms.positions[i])
            unit_cell = replicated_atoms.cell / supercell

            atoms = Atoms(unit_symbols,
                          positions=unit_positions,
                          cell=unit_cell,
                          pbc=[1, 1, 1])


            _, _third_order = import_from_files(replicated_atoms=replicated_atoms,
                                                third_file=third_file,
                                                supercell=supercell,
                                                third_energy_threshold=third_energy_threshold)
            third_order = ThirdOrder(atoms, replicated_atoms.positions, supercell, _third_order)


        elif format == 'shengbte' or format == 'shengbte-qe':
            if format=='shengbte-qe':
                grid_type='C'
            else:
                grid_type='F'

            config_file = folder + '/' + 'CONTROL'
            try:
                atoms, supercell = shengbte_io.import_control_file(config_file)
            except FileNotFoundError as err:
                config_file = folder + '/' + 'POSCAR'
                logging.info('\nTrying to open POSCAR')
                atoms = ase.io.read(config_file)

            third_file = folder + '/' + 'FORCE_CONSTANTS_3RD'

            third_order = shengbte_io.read_third_order_matrix(third_file, atoms, supercell, order='C')
            third_order = ThirdOrder.from_supercell(atoms,
                                                    grid_type=grid_type,
                                                    supercell=supercell,
                                                    force_constant=third_order)

        elif format == 'hiphive':
            filename = 'atom_prim.xyz'
            # TODO: add replicated filename in example
            replicated_filename = 'replicated_atoms.xyz'
            try:
                import kaldo.interface.hiphive_io as hiphive_io
            except ImportError:
                logging.error('In order to use hiphive along with kaldo, hiphive is required. \
                      Please consider installing hihphive. More info can be found at: \
                      https://hiphive.materialsmodeling.org/')

            atom_prime_file = str(folder) + '/' + filename
            replicated_atom_prime_file = str(folder) + '/' + replicated_filename
            # TODO: Make this independent of replicated file
            atoms = ase.io.read(atom_prime_file)
            replicated_atoms = ase.io.read(replicated_atom_prime_file)

            if 'model3.fcs' in os.listdir(str(folder)):
                # Derive constants used for third-order reshape
                supercell = np.array(supercell)
                n_prim = atoms.copy().get_masses().shape[0]
                n_sc = np.prod(supercell)
                dim = len(supercell[supercell > 1])
                _third_order = hiphive_io.import_third_from_hiphive(atoms, supercell, folder)
                _third_order = _third_order[0].reshape(n_prim * dim, n_sc * n_prim * dim,
                                                                       n_sc * n_prim * dim)
                third_order = cls(atoms,
                                                           replicated_atoms.positions,
                                                           supercell,
                                                           _third_order)


        else:
            raise ValueError
        return third_order


    def save(self, out_format='eskm', out_filename='THIRD', min_force=1e-6):
        if out_format == 'eskm':
            logging.info('Exporting third in eskm format')
            n_atoms = self.n_atoms
            n_replicas = self.n_replicas
            n_replicated_atoms = n_atoms * n_replicas
            tenjovermoltoev = 10 * units.J / units.mol
            third = self.third_order.value.reshape((n_atoms, 3, n_replicated_atoms, 3, n_replicated_atoms, 3)) / tenjovermoltoev
            with open(out_filename, 'w') as out_file:
                for i in range(n_atoms):
                    for alpha in range(3):
                        for j in range(n_replicated_atoms):
                            for beta in range(3):
                                value = third[i, alpha, j, beta].todense()
                                mask = np.argwhere(np.linalg.norm(value, axis=1) > min_force)
                                if mask.any():
                                    for k in mask:
                                        k = k[0]
                                        out_file.write("{:5d} ".format(i + 1))
                                        out_file.write("{:5d} ".format(alpha + 1))
                                        out_file.write("{:5d} ".format(j + 1))
                                        out_file.write("{:5d} ".format(beta + 1))
                                        out_file.write("{:5d} ".format(k + 1))
                                        for gamma in range(3):
                                            out_file.write(' {:16.6f}'.format(third[i, alpha, j, beta, k, gamma]))
                                        out_file.write('\n')
            logging.info('Done exporting third.')
        else:
            raise ValueError('Output: ' + out_format + ', non implemented.')


    def __str__(self):
        return 'third'