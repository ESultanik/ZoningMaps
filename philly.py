# Philadelphia-specific zoning information for residential properties

import math

AVERAGE_PEOPLE_PER_HOUSEHOLD = 2.35

class ResidentialPermittedUses(object):
    USES = frozenset(['single_family', 'duplex', 'multi_family', 'residential_related', 'non_residential', 'other_uses', 'hotel', 'commercial'])
    def __init__(self, **kwargs):
        for arg in kwargs:
            if arg not in self.USES:
                raise TypeError("got an unexpected keyword argument '%s'" % arg)
            setattr(self, arg, kwargs[arg])
        for arg in self.USES:
            if not hasattr(self, arg):
                setattr(self, arg, False)

class BuildingType(object):
    def __init__(self, detached = False, semi_detached = False, attached = False, multiple = False):
        self.detached = detached
        self.semi_detached = semi_detached
        self.attached = attached
        self.multiple = multiple

class ZoningRequirements(object):
    def __init__(self, minimum_lot_area, height_limit, minimum_households, maximum_households):
        self.minimum_lot_area = minimum_lot_area
        self.height_limit = height_limit
        self.minimum_households = minimum_households
        self.maximum_households = maximum_households
        self.residents_lower_bound = minimum_households * AVERAGE_PEOPLE_PER_HOUSEHOLD
        self.residents_upper_bound = maximum_households * AVERAGE_PEOPLE_PER_HOUSEHOLD
        
class ZoningDistrict(object):
    def __init__(self, name, uses, building_type, sqft_estimator, household_estimator):
        self.name = name
        self.uses = uses
        self.building_type = building_type
        self.sqft_estimator = sqft_estimator
        self.household_estimator = household_estimator
    def estimate_maximum_sqft(self, lot_area):
        return self.sqft_estimator(lot_area)
    def estimate_maximum_households(self, lot_area):
        return self.household_estimator(lot_area)
    def resident_bounds(self, lot_area):
        min_households = 1
        max_households = self.estimate_maximum_households(lot_area)
        return min_households * AVERAGE_PEOPLE_PER_HOUSEHOLD, max_households * AVERAGE_PEOPLE_PER_HOUSEHOLD

class ConstantHouseholdEstimator(object):
    def __init__(self, maximum_households):
        self.maximum_households = maximum_households
    def __call__(self, lot_area):
        return self.maximum_households

class GrossFloorAreaEstimator(object):
    def __init__(self, gross_floor_area_percent):
        self.gross_floor_area = gross_floor_area_percent
    def __call__(self, lot_area):
        return float(lot_area) * float(self.gross_floor_area) / 100.0

class GrossFloorAreaHouseholdEstimator(GrossFloorAreaEstimator):
    def __init__(self, gross_floor_area_percent, square_feet_per_resident = 450.0):
        super(GrossFloorAreaHouseholdEstimator, self).__init__(gross_floor_area_percent)
        self.square_feet_per_resident = square_feet_per_resident
    def __call__(self, lot_area):
        return int(math.ceil((super(GrossFloorAreaHouseholdEstimator, self)(lot_area) / self.square_feet_per_resident) / AVERAGE_PEOPLE_PER_HOUSEHOLD))

class MaximumFloorsEstimator(object):
    def __init__(self, minimum_open_area_percentage, maximum_floors):
        self.minimum_open_area_percentage = minimum_open_area_percentage
        self.maximum_floors = maximum_floors
    def __call__(self, lot_area):
        return lot_area * (1.0 - self.minimum_open_area_percentage) * self.maximum_floors

class MaximumFloorsHouseholdEstimator(MaximumFloorsEstimator):
    def __init__(self, minimum_open_area_percentage, maximum_floors, square_feet_per_resident = 450.0):
        super(MaximumFloorsEstimator, self).__init__(minimum_open_area_percentage, maximum_floors)
        self.square_feet_per_resident = square_feet_per_resident
    def __call__(self, lot_area):
        return int(math.ceil((super(MaximumFloorsHouseholdEstimator, self)(lot_area) / self.square_feet_per_resident) / AVERAGE_PEOPLE_PER_HOUSEHOLD))
    
ZONING = {}

def _add_district(name, uses, btype, sqft_estimator, household_estimator):
    ZONING[name] = ZoningDistrict(name,
                                  ResidentialPermittedUses(**dict([(use, True) for use in uses])),
                                  BuildingType(**dict([(t, True) for t in btype])),
                                  household_estimator)

# PRE-2012:
_add_district("R1",  ['single_family', 'other_uses'], ['detached'], ConstantHouseholdEstimator(1))
_add_district("R1A", ['single_family', 'other_uses'], ['detached'], ConstantHouseholdEstimator(1))
_add_district("R2",  ['single_family', 'other_uses'], ['detached'], ConstantHouseholdEstimator(1))
_add_district("R3",  ['single_family', 'residential_related', 'non_residential'], ['detached', 'semi_detached'], ConstantHouseholdEstimator(1))
_add_district("R4",  ['single_family', 'residential_related', 'non_residential'], ['detached', 'semi_detached'], ConstantHouseholdEstimator(1))
_add_district("R5",  ['single_family', 'residential_related', 'non_residential'], ['detached', 'semi_detached'], ConstantHouseholdEstimator(1))
_add_district("R5A", ['single_family', 'duplex', 'residential_related', 'non_residential'], ['detached', 'semi_detached'], ConstantHouseholdEstimator(2))
_add_district("R6",  ['single_family', 'residential_related', 'non_residential'], ['detached', 'semi_detached', 'attached'], ConstantHouseholdEstimator(1))
_add_district("R7",  ['single_family', 'duplex', 'residential_related', 'non_residential'], ['detached', 'semi_detached', 'attached'], ConstantHouseholdEstimator(2))
_add_district("R8",  ['single_family', 'duplex', 'residential_related', 'non_residential'], ['detached', 'semi_detached', 'attached'], ConstantHouseholdEstimator(2))
# For R-9, minimum lot area is 1440 sqft. with a minimum open area of 30% of the lot (20% for corner lots)
# The average Philly block is 250000 square feet, so the % of an average block taken by corner R-9 lots is
# 1440*4/250000 ~= 2%. But let's be generous and say that there are two minor streets running throug the block,
# allowing for 16 corners per whole block. So that's 1440*16/250000 ~= 9%. So let's say the average minimum open area
# of a R-9 lot is 29.1% of the lot.
_add_district("R9",  ['single_family', 'duplex', 'multi_family', 'residential_related', 'non_residential'], ['detached', 'semi_detached', 'attached'], MaximumFloorsHouseholdEstimator(0.291, 3))
_add_district("R9A", ['single_family', 'residential_related', 'non_residential'], ['detached', 'semi_detached', 'attached'], ConstantHouseholdEstimator(1))
_add_district("R10", ['single_family', 'duplex', 'multi_family', 'residential_related', 'non_residential'], ['detached', 'semi_detached', 'attached'], MaximumFloorsHouseholdEstimator(0.291, 3))
_add_district("R10A",['single_family', 'residential_related', 'non_residential'], ['detached', 'semi_detached', 'attached'], ConstantHouseholdEstimator(1))
_add_district("R10B",['single_family', 'duplex', 'other_uses'], ['detached', 'semi_detached', 'attached', 'multiple'], ConstantHouseholdEstimator(2))
_add_district("R11", ['single_family', 'duplex', 'multi_family', 'other_uses'], ['detached', 'semi_detached', 'attached', 'multiple'], GrossFloorAreaHouseholdEstimator(30))
_add_district("R11A",['single_family', 'duplex', 'multi_family', 'other_uses'], ['detached', 'semi_detached', 'attached', 'multiple'], GrossFloorAreaHouseholdEstimator(50))
_add_district("R12", ['single_family', 'duplex', 'multi_family', 'other_uses'], ['detached', 'semi_detached', 'attached', 'multiple'], GrossFloorAreaHouseholdEstimator(70))
_add_district("R13", ['single_family', 'duplex', 'multi_family', 'other_uses'], ['detached', 'semi_detached', 'attached', 'multiple'], GrossFloorAreaHouseholdEstimator(150))
_add_district("R14", ['single_family', 'duplex', 'multi_family', 'residential_related', 'non_residential'], ['detached', 'semi_detached'], GrossFloorAreaHouseholdEstimator(150))
_add_district("R15", ['single_family', 'duplex', 'multi_family', 'residential_related', 'non_residential', 'other_uses'], ['detached', 'semi_detached', 'attached'], GrossFloorAreaHouseholdEstimator(350))
_add_district("R16", ['single_family', 'duplex', 'multi_family', 'residential_related', 'non_residential', 'hotel'], ['detached', 'semi_detached', 'attached', 'multiple'], GrossFloorAreaHouseholdEstimator(500))
_add_district("R18", ['single_family', 'duplex', 'multi_family', 'residential_related', 'non_residential'], ['detached', 'semi_detached', 'attached'], MaximumFloorsHouseholdEstimator(.55, 3))
_add_district("R19", ['single_family', 'duplex', 'multi_family', 'residential_related', 'non_residential'], ['detached', 'semi_detached', 'attached'], MaximumFloorsHouseholdEstimator(.5, 5))
_add_district("R20", ['single_family', 'residential_related', 'non_residential'], ['detached', 'semi_detached', 'attached', 'multiple'], GrossFloorAreaHouseholdEstimator(177))
_add_district("RC1", ['single_family', 'hotel'], ['detached', 'semi_detached', 'attached', 'multiple'], GrossFloorAreaHouseholdEstimator(135))
_add_district("RC2", ['single_family', 'residential_related', 'non_residential', 'hotel'], ['detached', 'semi_detached'], GrossFloorAreaHouseholdEstimator(150))
_add_district("RC3", ['single_family', 'residential_related', 'non_residential', 'hotel'], ['detached', 'semi_detached', 'attached', 'multiple'], GrossFloorAreaHouseholdEstimator(350))
_add_district("RC4", ['single_family', 'residential_related', 'non_residential', 'hotel'], ['detached', 'semi_detached', 'attached', 'multiple'], GrossFloorAreaHouseholdEstimator(500))
_add_district("RC6", ['single_family', 'residential_related'], ['detached', 'semi_detached', 'attached', 'multiple'], GrossFloorAreaHouseholdEstimator(150))

# CURRENT:
_add_district("RSD-1", ['single_family'], ['detached'], ConstantHouseholdEstimator(1))
_add_district("RSD-2", ['single_family'], ['detached'], ConstantHouseholdEstimator(1))
_add_district("RSD-3", ['single_family'], ['detached'], ConstantHouseholdEstimator(1))
_add_district("RSA-1", ['single_family'], ['detached', 'semi_detached'], ConstantHouseholdEstimator(1))
_add_district("RSA-2", ['single_family'], ['detached', 'semi_detached'], ConstantHouseholdEstimator(1))
_add_district("RSA-3", ['single_family'], ['detached', 'semi_detached'], ConstantHouseholdEstimator(1))
_add_district("RSA-4", ['single_family'], ['detached', 'semi_detached', 'attached'], ConstantHouseholdEstimator(1))
_add_district("RSA-5", ['single_family'], ['detached', 'semi_detached', 'attached'], ConstantHouseholdEstimator(1))
_add_district("RTA-1", ['single_family', 'duplex'], ['detached', 'semi_detached'], ConstantHouseholdEstimator(2))
_add_district("RM-1",  ['single_family', 'duplex', 'multi_family'], ['detached', 'semi_detached', 'attached', 'multiple'], MaximumFloorsHouseholdEstimator(.3, 3))
_add_district("RM-2",  ['single_family', 'duplex', 'multi_family'], ['detached', 'semi_detached', 'attached', 'multiple'], GrossFloorAreaHouseholdEstimator(70))
_add_district("RM-3",  ['single_family', 'duplex', 'multi_family'], ['detached', 'semi_detached', 'attached', 'multiple'], GrossFloorAreaHouseholdEstimator(150))
_add_district("RM-4",  ['single_family', 'duplex', 'multi_family'], ['detached', 'semi_detached', 'attached', 'multiple'], GrossFloorAreaHouseholdEstimator(350))
_add_district("RMX-1", ['single_family', 'duplex', 'multi_family'], ['detached', 'semi_detached', 'attached', 'multiple'], GrossFloorAreaHouseholdEstimator(150))
_add_district("RMX-2", ['single_family', 'duplex', 'multi_family'], ['detached', 'semi_detached', 'attached', 'multiple'], GrossFloorAreaHouseholdEstimator(250))
_add_district("RMX-3", ['single_family', 'duplex', 'multi_family'], ['detached', 'semi_detached', 'attached', 'multiple'], GrossFloorAreaHouseholdEstimator(600))
_add_district("CMX-1", ['single_family'], ['attached'], ConstantHouseholdEstimator(1))
_add_district("CMX-2", ['single_family'], ['attached'], MaximumFloorsHouseholdEstimator(0.25, 4))
_add_district("CMX-2.5", ['single_family'], ['attached'], MaximumFloorsHouseholdEstimator(0.25, 5))
_add_district("CMX-3", ['single_family'], ['attached'], GrossFloorAreaHouseholdEstimator(800 * 0.75))
_add_district("CMX-4", ['single_family'], ['attached'], GrossFloorAreaHouseholdEstimator(1100))
_add_district("CMX-5", ['single_family'], ['attached'], GrossFloorAreaHouseholdEstimator(2000))
_add_district("IRMX", ['single_family'], ['attached'], GrossFloorAreaHouseholdEstimator(500))
_add_district("ICMX", ['single_family'], ['attached'], GrossFloorAreaHouseholdEstimator(500))
