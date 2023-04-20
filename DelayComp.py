from mdfimport import *

import os
import numpy as np

import matplotlib.pyplot as plt

from tqdm import tqdm

from fpdf import FPDF
import base64
import tempfile


class DelayComp():

    def __init__(self, path):

        self.path = path
        self.file = os.listdir(path)

        # print(self.file)

        self.time_step_min   = 0.5
        self.settle_time_pct = 0.5

    def _filtro_nan(self, data, column):

        return data[~data[column].isna()].reset_index(drop=True)


    def delay_comp_process(self, channel_list):

        figs = []

        curves = []
        for file in self.file:

            path = self.path + '/' + file
            # path = file

            mdf  = MDFImport(path, channel_list)
            data = mdf.MDF_to_pandas()

            data_cmd  = self._filtro_nan(data, 'IsdCmd')
            data_TqFB = self._filtro_nan(data, 'Mech_out_M')

            Id_diff = [data_cmd['IsdCmd'][i+1]-data_cmd['IsdCmd'][i] for i in range(len(data_cmd)-1)]
            Id_diff.insert(0, 0)

            test_id    = [id_d != 0 for id_d in Id_diff]
            time_trans = data_cmd[test_id]['time'].values
            time_diff  = [time_trans[i+1]-time_trans[i] for i in range(len(time_trans)-1)]

            rng   = [time_d > self.time_step_min for time_d in time_diff]
            idx   = max([index for index, item in enumerate(rng) if item == True])
            idx_n = idx + 1 if idx + 1 < len(rng) else len(rng)-1
            rng[idx_n] = True

            time_start = time_trans[rng.index(True)]
            time_end   = time_trans[idx]
            step_times = [time_trans[idx] for idx, r in enumerate(rng) if r == True]


            Iangle, TqFB = [], []
            for s in tqdm(range(len(step_times)-1)):

                tend   = step_times[s+1]
                tstart = step_times[s] + (tend-step_times[s])*self.settle_time_pct

                test  = [r > tstart and r < tend for idx, r in enumerate(data_cmd['time'])]
                IdCmd = [data_cmd['IsdCmd'][idx] for idx, r in enumerate(test) if (r == True)]
                IqCmd = [data_cmd['IsqCmd'][idx] for idx, r in enumerate(test) if (r == True)]

                if (IdCmd != []) and (IqCmd != []):

                    IdCmd_mean = np.asarray(IdCmd).mean()
                    IqCmd_mean = np.asarray(IqCmd).mean()

                    arc_tg = np.arctan2(-IdCmd_mean, IqCmd_mean) * 180 / np.pi

                    test  = [r > tstart and r < tend for idx, r in enumerate(data_TqFB['time'])]
                    TqFB_ = [data_TqFB['Mech_out_M'][idx] for idx, r in enumerate(test) if (r == True)]

                    if (TqFB_ != []):

                        Iangle.append(arc_tg)
                        TqFB.append(np.mean(TqFB_))

            p    = np.polyfit(Iangle, TqFB, 1)
            Imag = np.sqrt(IdCmd_mean**2 + IqCmd_mean**2)
            Spd  = round(data['VeMtrCtrl_n_Out_MotorSpeed_RPM_T1'].mean(), -2) 

            print(p)

            curves.append((Spd, TqFB, Iangle, p))  

        act_speed = None
        proc_curves, inter = [], []
        for idx, (Spd, TqFB, Iangle, p) in enumerate(curves): 

            if Spd == act_speed:
                inter.append((Spd, TqFB, Iangle, p))

            else:
                if act_speed is None:
                    act_speed = Spd
                    inter.append((Spd, TqFB, Iangle, p))

                else:
                    proc_curves.append(inter)
                    inter = [(Spd, TqFB, Iangle, p)]
                    act_speed = Spd

            if idx == len(curves)-1:
                proc_curves.append(inter)

        for curve in proc_curves: 

            fig = plt.figure(figsize=(10, 8))
            for Spd, TqFB, Iangle, p in curve:      

                plt.plot(Iangle, TqFB)
                plt.plot(Iangle, np.polyval(p, Iangle))

            plt.title(f'Torque vs Current Angle: {Spd} RPM')
            plt.ylabel('Torque [Nm]')
            plt.xlabel('Current Angle [deg]')

            plt.grid()
            figs.append(fig)

        ang_err, torq, speeds = [], [], []
        for speed in set([Spd for Spd, TqFB, Iangle, p in curves]):

            speed_m = [(Spd, TqFB, Iangle, p) for Spd, TqFB, Iangle, p in curves if Spd == speed]

            if len(speed_m) >= 2:

                dm = speed_m[0][3][0] - speed_m[1][3][0]
                db = speed_m[1][3][1] - speed_m[0][3][1]

                ang_isect = db/dm

            ang_err.append(90 - ang_isect)
            torq.append(speed_m[0][3][0]*ang_isect + speed_m[0][3][1])
            speeds.append(speed)

        results = {'Speed'  : speeds,
                   'AngErr' : ang_err,
                   'Torque' : torq}
        
        data_results = pd.DataFrame(results)
        data_results = data_results.sort_values(by='Speed')

        print(data_results)

        p      = np.polyfit(data_results['Speed'], data_results['AngErr'], 1)
        sp_fit = [data_results['Speed'].max(), data_results['Speed'].min()]
        AngFit = np.polyval(p, sp_fit)

        fig = plt.figure(figsize=(10, 8))

        plt.plot(data_results['Speed'], data_results['AngErr'], marker='+')
        plt.plot(sp_fit, AngFit)

        plt.title(f'Angle Error x Speed')
        plt.ylabel('Speed [RPM]')
        plt.xlabel('Angle Error [deg]')
        plt.grid(True)

        figs.append(fig)

        fig = plt.figure(figsize=(10, 8))

        plt.plot(data_results['Speed'], data_results['Torque'], marker='+')       

        plt.title(f'Torque Intersection Point x Speed')
        plt.ylabel('Speed [RPM]')
        plt.xlabel('Torque Intersection [Nm]')
        plt.grid(True)

        figs.append(fig)

        self.figs = figs

    def export_as_pdf(self, plots, titles, legend, bbox):


        pdf = FPDF('L', 'mm', 'A4')  

        # OVERVIEW ===========================================

        pdf.add_page()
        pdf.set_font('Times', 'B', 36)
        pdf.image('header.png', x=0, y=0, w=297)
        pdf.cell(0, 150, 'Delay Comp', align='C')



        # for plot, title in zip(plots, titles):

        for plot in self.figs:
        
            pdf.add_page()
            pdf.image('header.png', x=0, y=0, w=297)

            pdf.set_font('Times', 'B', 18)
            pdf.set_text_color(255)
            pdf.cell(0, 0, 'title', align='L')


            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                plot.savefig(tmpfile.name, bbox_inches="tight")
                pdf.image(tmpfile.name, x=10, y=40,  w=190)

            # with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
            #     legend.savefig(tmpfile.name, dpi="figure", bbox_inches=bbox)
            #     pdf.image(tmpfile.name, x=263, y=25,  w=25)

        
        return pdf






if __name__ == '__main__':

    channel_list = ['VeMtrCtrl_n_Out_MotorSpeed_RPM_T1', 
                    'HV_Volt', 
                    'IsdCmd', 
                    'IsqCmd', 
                    'CurrentSweepingObj.CurrentSweeper.Variables.ITheta',
                    'Mech_out_M']

    path = 'DelayCompR6 20230317'
    DC   = DelayComp(path)

    DC.delay_comp_process(channel_list=channel_list)
    pdf = DC.export_as_pdf(plots=None, titles=None, legend=None, bbox=None)
    pdf.output('DelayCompTest.pdf')