import mdfreader
import pandas    as pd

class MDFImport():

    def __init__(self, path, channel_list=None):


        self.mdf = mdfreader.Mdf(path, channel_list=channel_list)


    def MDF_to_dict(self):

        channels = self.mdf.masterChannelList

        # Dictionary with the data 
        channels_data = {}
        for channel in channels:
            inter = {}

            for idx, name in enumerate(channels[channel]):
                inter[name] = self.mdf.get_channel(channels[channel][idx])['data']

            channels_data[channel] = inter

        return channels_data


    def MDF_to_pandas(self):

        channels_data = self.MDF_to_dict()

        # Dictionary with the DataFrame
        channels_frame = {}
        for key in channels_data.keys():

            channels_frame[key] = pd.DataFrame(channels_data[key])
            channels_frame[key] = channels_frame[key].rename(columns={key:'time'})


        data = pd.DataFrame()
        for key in channels_frame.keys():

            if len(data) == 0:
                data = channels_frame[key]

            else:
                data = data.merge(channels_frame[key], on='time', how='outer')


        data = data.sort_values(by='time')
        # data = data.interpolate()

        # for col in data.columns:

        #     value = data[~data[col].isna()][col].values[0]

        #     data[col] = data[col].fillna(value)

        data = data.reset_index(drop=True)

        return data


    def MDF_to_CSV(self, path):

        data = self.MDF_to_pandas(path)

        data.to_csv(path, index=False)






if __name__ == '__main__':

    channel_list = ['VeMtrCtrl_n_Out_MotorSpeed_RPM_T1', 
                    'HV_Volt', 
                    'IsdCmd', 
                    'IsqCmd', 
                    'CurrentSweepingObj.CurrentSweeper.Variables.ITheta']

