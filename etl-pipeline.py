import pandas as pd
import argparse
import datetime
import logging

import apache_beam as beam
from apache_beam.io import WriteToBigQuery
from apache_beam.io.gcp.gcsio import GcsIO
from apache_beam.io.filebasedsource import FileBasedSource
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import SetupOptions

# import dotenv
# dotenv.load_dotenv()

PROJECT_ID = 'assetinsure-surety-data-models'
BUCKET = 'gs://surety-data-models'
TABLE_SPEC = f'{PROJECT_ID}:ls_panthers_test.panters-test-table-1'

table_schema = {
        'fields': [
            {'name': 'ID', 'type': 'NUMERIC'},
            {'name': 'CompanyName', 'type': 'STRING'},
            {'name': 'Date', 'type': 'DATETIME'}
        ]
    }

class ExcelSource(FileBasedSource):
    def __init__(self, file_pattern):
        super().__init__(file_pattern, splittable=False)

    def read_records(self, file_name, range_tracker):
        # Use pandas to read the Excel file
        with GcsIO().open(file_name) as f:
            df = pd.read_excel(f)

        yield df

def process_excel_file(df):
    # Get the DataFrame from the list
    # Find the first row index where the first column is not null
    first_non_null_index = df[df.iloc[:, 0].notnull()].index[0]
    # Extract rows from the first non-null cell in the first column onwards
    company_name = df.iloc[first_non_null_index, 0]
    print(company_name)

    # Get the current date and time
    current_time = datetime.datetime.now()
    # Print the current time
    print(current_time)

    # Create a dictionary to represent the row data
    row_data = {
        'ID': 1,  # Replace with the actual ID if available
        'CompanyName': company_name,
        'Date': current_time
    }

    # Return the row data as a dictionary
    return row_data

def run(argv=None, save_main_session = True):
    parser = argparse.ArgumentParser()
    # parser.add_argument('--my-arg', help='description')
    args, beam_args = parser.parse_known_args()

    # Create and set your PipelineOptions.
    # For Cloud execution, specify DataflowRunner and set the Cloud Platform
    # project, job name, temporary files location, and region.
    # For more information about regions, check:
    # https://cloud.google.com/dataflow/docs/concepts/regional-endpoints
    pipeline_options = PipelineOptions(
        beam_args,
        runner='DataflowRunner',
        project=PROJECT_ID,
        job_name='test-2-ls',
        temp_location=f'{BUCKET}/temp/',
        region='europe-west2')
    # Note: Repeatable options like dataflow_service_options or experiments must
    # be specified as a list of string(s).
    # e.g. dataflow_service_options=['enable_prime']
    pipeline_options.view_as(SetupOptions).save_main_session = save_main_session

    with beam.Pipeline(options=pipeline_options) as p:

        excel_data = (
            p
            | 'Read Excel Files' >> beam.io.Read(ExcelSource(f'{BUCKET}/input/*.xlsm'))
            | 'Transform Data' >> beam.Map(process_excel_file)
        )

        excel_data | 'Write to BigQuery' >> WriteToBigQuery(
            table=TABLE_SPEC,
            schema=table_schema,
            create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
            write_disposition=beam.io.BigQueryDisposition.WRITE_TRUNCATE,
            custom_gcs_temp_location=f'{BUCKET}/temp/'
        )

if __name__ == '__main__':
  logging.getLogger().setLevel(logging.INFO)
  run()
