import streamlit as st
import pandas    as pd

from __init__ import *
from io import StringIO

import pickle, base64

# CREATE DOWNLOAD LINK

def create_download_link(val, filename):
    b64 = base64.b64encode(val)  # val looks like b'...'
    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{filename}.pdf">Download file</a>'


st.set_page_config(layout='wide')

st.title(':black[Delay Comp Report Generator]')
st.markdown('---')

delayComps = st.file_uploader('Upload Document', type=['dat'], accept_multiple_files=True)

path      = st.text_input('Path')

speed      = st.text_input('Speed [RPM]'         , 'VeMtrCtrl_n_Out_MotorSpeed_RPM_T1')
voltage    = st.text_input('Voltage [V]'         , 'HV_Volt')
IsdCmd     = st.text_input('IsdCmd [A]'          , 'IsdCmd')
IsqCmd     = st.text_input('IsqCmd [A]'          , 'IsqCmd')
ITheta     = st.text_input('Theta [rad]'         , 'CurrentSweepingObj.CurrentSweeper.Variables.ITheta')
Mech_out_M = st.text_input('Mechanical Power [W]', 'Mech_out_M')

if st.button('Generate Report'):

    print(delayComps)

    channel_list = [speed, voltage, IsdCmd, IsqCmd, ITheta, Mech_out_M]

    # delayComps = [StringIO(delayComp.getvalue()) for delayComp in delayComps] #.decode('unicode_escape')
    # print(delayComps)
    delayComps = [StringIO(delayComp.getvalue().decode('ISO-8859-1')) for delayComp in delayComps]
    print(delayComps)

    DC = DelayComp(path)

    # Generate PDF
    DC.delay_comp_process(channel_list=channel_list)
    pdf = DC.export_as_pdf(plots=None, titles=None, legend=None, bbox=None)
    pdf.output('DelayCompTest.pdf')
