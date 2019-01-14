"""
Tax-Calculator CorpRecords class.
"""
# CODING-STYLE CHECKS:
# pycodestyle records.py
# pylint --disable=locally-disabled records.py

import os
import json
import numpy as np
import pandas as pd
from taxcalc.growfactors import GrowFactors


class CorpRecords(object):
    """
    Constructor for the corporate-tax-filing-unit CorpRecords class.

    Parameters
    ----------
    data: string or Pandas DataFrame
        string describes CSV file in which records data reside;
        DataFrame already contains records data;
        default value is the string 'cit.csv'
        For details on how to use your own data with the Tax-Calculator,
        look at the test_Calculator_using_nonstd_input() function in the
        tests/test_calculate.py file.

    data_type: string of type of data to use;
        May be "cross-section" or "panel"

    gfactors: GrowFactors class instance or None
        containing record data extrapolation (or "blowup") factors.
        NOTE: the constructor should never call the _blowup() method.

    weights: string or Pandas DataFrame or None
        string describes CSV file in which weights reside;
        DataFrame already contains weights;
        None creates empty sample-weights DataFrame;
        default value is filename of the CIT weights.

    start_year: integer
        specifies assessment year of the input data;
        default value is CITCSV_YEAR.
        Note that if specifying your own data (see above) as being a custom
        data set, be sure to explicitly set start_year to the
        custom data's assessment year.

    Raises
    ------
    ValueError:
        if data is not the appropriate type.
        if gfactors is not None or a GrowFactors class instance.
        if start_year is not an integer.
        if files cannot be found.

    Returns
    -------
    class instance: CorpRecords

    Notes
    -----
    Typical usage when using CIT input data is as follows::

        crecs = CorpRecords()

    which uses all the default parameters of the constructor, and
    therefore, imputed variables are generated to augment the data and
    initial-year grow factors are applied to the data.  There are
    situations in which you need to specify the values of the CorpRecord
    constructor's arguments, but be sure you know exactly what you are
    doing when attempting this.
    """
    # suppress pylint warnings about unrecognized Records variables:
    # pylint: disable=no-member
    # suppress pylint warnings about uppercase variable names:
    # pylint: disable=invalid-name
    # suppress pylint warnings about too many class instance attributes:
    # pylint: disable=too-many-instance-attributes

    CITCSV_YEAR = 2017

    CUR_PATH = os.path.abspath(os.path.dirname(__file__))
    CIT_DATA_FILENAME = 'cit.csv'
    CIT_WEIGHTS_FILENAME = 'cit_weights.csv'
    VAR_INFO_FILENAME = 'corprecords_variables.json'

    def __init__(self,
                 data=CIT_DATA_FILENAME,
                 data_type='cross-section',
                 gfactors=GrowFactors(),
                 weights=CIT_WEIGHTS_FILENAME,
                 start_year=CITCSV_YEAR):
        # pylint: disable=too-many-arguments,too-many-locals
        self.__data_year = start_year
        # read specified data
        if data_type == 'cross-section':
            self.data_type = data_type
        elif data_type == 'panel':
            self.data_type = data_type
            raise ValueError('Panel methods not yet built')
        else:
            raise ValueError('data_type is not cross-section or panel')
        self._read_data(data)
        # handle grow factors
        is_correct_type = isinstance(gfactors, GrowFactors)
        if gfactors is not None and not is_correct_type:
            msg = 'gfactors is neither None nor a GrowFactors instance'
            raise ValueError(msg)
        self.gfactors = gfactors
        # read sample weights
        self.WT = None
        self._read_weights(weights)
        # weights must be same size as tax record data
        if self.WT.size > 0 and self.array_length != len(self.WT.index):
            # scale-up sub-sample weights by year-specific factor
            sum_full_weights = self.WT.sum()
            self.WT = self.WT.iloc[self.__index]
            sum_sub_weights = self.WT.sum()
            factor = sum_full_weights / sum_sub_weights
            self.WT *= factor
        # specify current_year and ASSESSMENT_YEAR values
        if isinstance(start_year, int):
            self.__current_year = start_year
            self.ASSESSMENT_YEAR.fill(start_year)
        else:
            msg = 'start_year is not an integer'
            raise ValueError(msg)
        # construct sample weights for current_year
        if self.WT.size > 0:
            wt_colname = 'WT{}'.format(self.current_year)
            if wt_colname in self.WT.columns:
                self.weight = self.WT[wt_colname]

    @property
    def data_year(self):
        """
        CorpRecords class original data year property.
        """
        return self.__data_year

    @property
    def current_year(self):
        """
        CorpRecords class current assessment year property.
        """
        return self.__current_year

    @property
    def array_length(self):
        """
        Length of arrays in CorpRecords class's DataFrame.
        """
        return self.__dim

    def increment_year(self):
        """
        Add one to current year.
        Also, does extrapolation, reweighting, adjusting for new current year.
        """
        # move to next year
        self.__current_year += 1
        # apply variable extrapolation grow factors
        if self.gfactors is not None:
            self._blowup(self.__current_year)
        # specify current-year sample weights
        if self.WT.size > 0:
            wt_colname = 'WT{}'.format(self.__current_year)
            self.weight = self.WT[wt_colname]

    def set_current_year(self, new_current_year):
        """
        Set current year to specified value and updates ASSESSMENT_YEAR 
        variable.
        Unlike increment_year method, extrapolation, reweighting, adjusting
        are skipped.
        """
        self.__current_year = new_current_year
        self.ASSESSMENT_YEAR.fill(new_current_year)

    @staticmethod
    def read_var_info():
        """
        Read CorpRecords variables metadata from JSON file;
        returns dictionary and specifies static varname sets listed below.
        """
        var_info_path = os.path.join(CorpRecords.CUR_PATH,
                                     CorpRecords.VAR_INFO_FILENAME)
        if os.path.exists(var_info_path):
            with open(var_info_path) as vfile:
                vardict = json.load(vfile)
        else:
            msg = 'file {} cannot be found'.format(var_info_path)
            raise ValueError(msg)
        CorpRecords.INTEGER_READ_VARS = set(k for k, v in vardict['read'].items()
                                        if v['type'] == 'int')
        FLOAT_READ_VARS = set(k for k, v in vardict['read'].items()
                              if v['type'] == 'float')
        CorpRecords.MUST_READ_VARS = set(k for k, v in vardict['read'].items()
                                     if v.get('required'))
        CorpRecords.USABLE_READ_VARS = CorpRecords.INTEGER_READ_VARS | FLOAT_READ_VARS
        INT_CALCULATED_VARS = set(k for k, v in vardict['calc'].items()
                                  if v['type'] == 'int')
        FLOAT_CALCULATED_VARS = set(k for k, v in vardict['calc'].items()
                                    if v['type'] == 'float')
        FIXED_CALCULATED_VARS = set(k for k, v in vardict['calc'].items()
                                    if v['type'] == 'unchanging_float')
        CorpRecords.CALCULATED_VARS = (INT_CALCULATED_VARS |
                                   FLOAT_CALCULATED_VARS |
                                   FIXED_CALCULATED_VARS)
        CorpRecords.CHANGING_CALCULATED_VARS = FLOAT_CALCULATED_VARS
        CorpRecords.INTEGER_VARS = CorpRecords.INTEGER_READ_VARS | INT_CALCULATED_VARS
        return vardict

    # specify various sets of variable names
    INTEGER_READ_VARS = None
    MUST_READ_VARS = None
    USABLE_READ_VARS = None
    CALCULATED_VARS = None
    CHANGING_CALCULATED_VARS = None
    INTEGER_VARS = None

    # ----- begin private methods of Records class -----

    def _blowup(self, year):
        """
        Apply to READ (not CALC) variables the grow factors for specified year.
        """
        # pylint: disable=too-many-locals,too-many-statements
        GF_CORP1 = self.gfactors.factor_value('CORP', year)
        self.NET_TAX_LIABILTY *= GF_CORP1

    def _read_data(self, data):
        """
        Read CorpRecords data from file or use specified DataFrame as data.
        """
        # pylint: disable=too-many-statements,too-many-branches
        if CorpRecords.INTEGER_VARS is None:
            CorpRecords.read_var_info()
        # read specified data
        if isinstance(data, pd.DataFrame):
            taxdf = data
        elif isinstance(data, str):
            data_path = os.path.join(CorpRecords.CUR_PATH, data)
            if os.path.exists(data_path):
                taxdf = pd.read_csv(data_path)
            else:
                msg = 'file {} cannot be found'.format(data_path)
                raise ValueError(msg)
        else:
            msg = 'data is neither a string nor a Pandas DataFrame'
            raise ValueError(msg)
        self.__dim = len(taxdf.index)
        self.__index = taxdf.index
        # create class variables using taxdf column names
        READ_VARS = set()
        self.IGNORED_VARS = set()
        for varname in list(taxdf.columns.values):
            if varname in CorpRecords.USABLE_READ_VARS:
                READ_VARS.add(varname)
                if varname in CorpRecords.INTEGER_READ_VARS:
                    setattr(self, varname,
                            taxdf[varname].astype(np.int32).values)
                else:
                    setattr(self, varname,
                            taxdf[varname].astype(np.float64).values)
            else:
                self.IGNORED_VARS.add(varname)
        # check that MUST_READ_VARS are all present in taxdf
        if not CorpRecords.MUST_READ_VARS.issubset(READ_VARS):
            msg = 'CorpRecords data missing one or more MUST_READ_VARS'
            raise ValueError(msg)
        # delete intermediate taxdf object
        del taxdf
        # create other class variables that are set to all zeros
        UNREAD_VARS = CorpRecords.USABLE_READ_VARS - READ_VARS
        ZEROED_VARS = CorpRecords.CALCULATED_VARS | UNREAD_VARS
        for varname in ZEROED_VARS:
            if varname in CorpRecords.INTEGER_VARS:
                setattr(self, varname,
                        np.zeros(self.array_length, dtype=np.int32))
            else:
                setattr(self, varname,
                        np.zeros(self.array_length, dtype=np.float64))
        # delete intermediate variables
        del READ_VARS
        del UNREAD_VARS
        del ZEROED_VARS

    def zero_out_changing_calculated_vars(self):
        """
        Set to zero all variables in the CorpRecords.CHANGING_CALCULATED_VARS.
        """
        for varname in CorpRecords.CHANGING_CALCULATED_VARS:
            var = getattr(self, varname)
            var.fill(0.)
        del var

    def _read_weights(self, weights):
        """
        Read CorpRecords weights from file or
        use specified DataFrame as data or
        create empty DataFrame if None.
        """
        if weights is None:
            setattr(self, 'WT', pd.DataFrame({'nothing': []}))
            return
        if isinstance(weights, pd.DataFrame):
            WT = weights
        elif isinstance(weights, str):
            weights_path = os.path.join(CorpRecords.CUR_PATH, weights)
            if os.path.isfile(weights_path):
                WT = pd.read_csv(weights_path)
        else:
            msg = 'weights is not None or a string or a Pandas DataFrame'
            raise ValueError(msg)
        assert isinstance(WT, pd.DataFrame)
        setattr(self, 'WT', WT.astype(np.float64))
        del WT
