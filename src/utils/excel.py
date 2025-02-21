import xlsxwriter
from typing import List, Any

def create_workbook(filename: str) -> xlsxwriter.Workbook:
    """Create and configure Excel workbook with formats"""
    print(f"Generating {filename} ...")
    workbook = xlsxwriter.Workbook(filename)
    return workbook

def setup_worksheet_formatting(workbook: xlsxwriter.Workbook, worksheet: xlsxwriter.Workbook.worksheet_class):
    """Setup worksheet with conditional formatting"""
    # Create formats
    cell_format = workbook.add_format()
    cell_format.set_bold()
    format1 = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
    format2 = workbook.add_format({'bg_color': ''})

    # Set basic formatting
    worksheet.set_column("A:A", None, cell_format)
    worksheet.set_row(0, None, cell_format)

    # Alert for "Alert" text in column B
    worksheet.conditional_format('B2:B200', {
        'type': 'cell',
        'criteria': '==',
        'value': '"Alert"',
        'format': format1
    })

    # Blank waffle end time
    worksheet.conditional_format('D2:D200', {
        'type': 'formula',
        'criteria': '=(ISBLANK(D2)=TRUE)',
        'stop_if_true': True,
        'format': format2
    })

    # Time difference alert
    worksheet.conditional_format('D2:D200', {
        'type': 'formula',
        'criteria': '=(($E2-$D2)>30/(24*60))',
        'format': format1
    })

    # Zero sales alert
    worksheet.conditional_format('F2:S200', {
        'type': 'cell',
        'criteria': '=',
        'value': 0,
        'format': format1
    })