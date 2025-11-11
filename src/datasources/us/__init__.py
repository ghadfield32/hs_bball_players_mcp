"""US DataSource Adapters."""

# National circuits
from .bound import BoundDataSource
from .eybl import EYBLDataSource
from .eybl_girls import EYBLGirlsDataSource
from .grind_session import GrindSessionDataSource
from .ote import OTEDataSource
from .rankone import RankOneDataSource
from .sblive import SBLiveDataSource
from .three_ssb import ThreeSSBDataSource

# Regional/State platforms
from .fhsaa import FHSAADataSource
from .hhsaa import HHSAADataSource
from .mn_hub import MNHubDataSource
from .psal import PSALDataSource
from .wsn import WSNDataSource

# State associations - Southeast
from .alabama_ahsaa import AHSAADataSource
from .arkansas_aaa import AAADataSource
from .georgia_ghsa import GHSADataSource
from .kentucky_khsaa import KHSAADataSource
from .louisiana_lhsaa import LHSAADataSource
from .mississippi_mhsaa import MHSAAMSDataSource
from .nchsaa import NCHSAADataSource
from .south_carolina_schsl import SCHSLDataSource
from .tennessee_tssaa import TSSAADataSource
from .virginia_vhsl import VHSLDataSource
from .west_virginia_wvssac import WVSSACDataSource

# State associations - Northeast
from .connecticut_ciac import CIACDataSource
from .delaware_diaa import DIAADataSource
from .maine_mpa import MPADataSource
from .maryland_mpssaa import MPSSAADataSource
from .massachusetts_miaa import MIAADataSource
from .nepsac import NEPSACDataSource
from .new_hampshire_nhiaa import NHIAADataSource
from .new_jersey_njsiaa import NJSIAADataSource
from .pennsylvania_piaa import PIAADataSource
from .rhode_island_riil import RIILDataSource
from .vermont_vpa import VPADataSource

# State associations - Midwest
from .indiana_ihsaa import IHSAADataSource
from .kansas_kshsaa import KSHSAADataSource
from .michigan_mhsaa import MHSAAMIDataSource
from .missouri_mshsaa import MSHSAADataSource
from .nebraska_nsaa import NSAADataSource
from .north_dakota_ndhsaa import NDHSAADataSource
from .ohio_ohsaa import OHSAADataSource

# State associations - Southwest/West
from .alaska_asaa import ASAADataSource
from .colorado_chsaa import CHSAADataSource
from .dc_dciaa import DCIAADataSource
from .montana_mhsa import MHSADataSource
from .new_mexico_nmaa import NMAADataSource
from .oklahoma_ossaa import OSSAADataSource
from .utah_uhsaa import UHSAADataSource
from .wyoming_whsaa import WHSAADataSource

__all__ = [
    # National circuits
    "BoundDataSource",
    "EYBLDataSource",
    "EYBLGirlsDataSource",
    "GrindSessionDataSource",
    "OTEDataSource",
    "RankOneDataSource",
    "SBLiveDataSource",
    "ThreeSSBDataSource",
    # Regional/State platforms
    "FHSAADataSource",
    "HHSAADataSource",
    "MNHubDataSource",
    "PSALDataSource",
    "WSNDataSource",
    # State associations - Southeast
    "AAADataSource",
    "AHSAADataSource",
    "GHSADataSource",
    "KHSAADataSource",
    "LHSAADataSource",
    "MHSAAMSDataSource",
    "NCHSAADataSource",
    "SCHSLDataSource",
    "TSSAADataSource",
    "VHSLDataSource",
    "WVSSACDataSource",
    # State associations - Northeast
    "CIACDataSource",
    "DIAADataSource",
    "MIAADataSource",
    "MPADataSource",
    "MPSSAADataSource",
    "NEPSACDataSource",
    "NHIAADataSource",
    "NJSIAADataSource",
    "PIAADataSource",
    "RIILDataSource",
    "VPADataSource",
    # State associations - Midwest
    "IHSAADataSource",
    "KSHSAADataSource",
    "MHSAAMIDataSource",
    "MSHSAADataSource",
    "NDHSAADataSource",
    "NSAADataSource",
    "OHSAADataSource",
    # State associations - Southwest/West
    "ASAADataSource",
    "CHSAADataSource",
    "DCIAADataSource",
    "MHSADataSource",
    "NMAADataSource",
    "OSSAADataSource",
    "UHSAADataSource",
    "WHSAADataSource",
]
