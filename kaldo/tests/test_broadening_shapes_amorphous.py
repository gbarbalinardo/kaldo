"""
Unit and regression test for the kaldo package.
"""

# Imports
from kaldo.forceconstants import ForceConstants
from kaldo.conductivity import Conductivity
from kaldo.phonons import Phonons
import ase.units as units
import numpy as np
import pytest

# NOTE: the scope of this fixture needs to be 'function' for these tests to work properly.
@pytest.yield_fixture(scope="function")
def phonons():
    print ("Preparing phonons object.")

    # Create a finite difference object
    forceconstants = ForceConstants.from_folder(folder='kaldo/tests/si-amorphous', format='eskm')

    # # Create a phonon object
    phonons = Phonons(forceconstants=forceconstants,
                      is_classic=True,
                      temperature=300,
                      third_bandwidth= 0.05 / 4.135,
                      storage='memory')
    return phonons


def test_gaussian_broadening(phonons):
    phonons.broadening_shape='gauss'
    np.testing.assert_approx_equal(phonons.bandwidth[0][250], 3.200066, significant=4)


def test_lorentz_broadening(phonons):
    phonons.broadening_shape='lorentz'
    phonons.is_tf_backend=False
    np.testing.assert_approx_equal(phonons.bandwidth[0][250], 3.358182, significant=4)


def test_triangle_broadening(phonons):
    phonons.broadening_shape='triangle'
    np.testing.assert_approx_equal(phonons.bandwidth[0][250], 3.358182, significant=4)