import _csv
import csv
import os
import sys

import pdfminer.pdfparser
import pdfplumber
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTRect, LTChar

csv.field_size_limit(int(sys.maxsize // 1e13))


class PDFParser:
    def __init__(self):
        self.intro_strs = 'введение', 'introduction'
        self.origins_strs = 'источник', 'литератур'
        self.lines_to_title_check = 10

    def parse_files(self, pdfs_directory, csv_filename=None, clear_csv=False):
        try:
            if csv_filename is None:
                csv_filename = './pdfs_data.csv'
            os.chdir(pdfs_directory)
            try:
                if clear_csv:
                    self.clear_csv(csv_filename)
                with open(f'../{csv_filename}', 'r', newline='', encoding='utf-8') as csvfile:
                    pdf_reader = csv.reader(csvfile)
                    pdfs = dict(pdf_reader)
            except FileNotFoundError:
                pdfs = {}

            pdf_filenames = sorted(filter(lambda x: x[-4:] == '.pdf', os.listdir()), reverse=True)
            for i, pdf_filename in enumerate(pdf_filenames):
                print(i, pdf_filename, end=' ')
                if pdf_filename[:-4] in pdfs:
                    print('skipped')
                else:
                    try:
                        pdfs[pdf_filename[:-4]] = self.parse_file(pdf_filename)
                        print('done')
                    except pdfminer.pdfparser.PDFSyntaxError:
                        print('pdf can not be opened')
        except Exception as e:
            print(e)
        finally:
            os.chdir('..')
            with open(csv_filename, 'w', newline='', encoding='utf-8') as csv_file:
                writer = csv.writer(csv_file)
                for pdf_filename, data in pdfs.items():
                    writer.writerow((pdf_filename, data))
            print('\ndata saved')

    def parse_file(self, pdf_path: str) -> str:
        pages = []

        start_page, stop_page = 0, None
        for page_num, page in enumerate(extract_pages(pdf_path)):
            page_elements = [(element.y1, element) for element in page._objs]
            page_elements.sort(key=lambda x: -x[0])

            for i in range(min(self.lines_to_title_check, len(page_elements))):
                page_title = page_elements[i][1]
                if not isinstance(page_title, LTTextContainer):
                    continue
                if not start_page and not any(
                        intro_str in page_title.get_text().lower() for intro_str in self.intro_strs):
                    continue
                if not start_page:
                    start_page = page_num
                if any(origins_str in page_title.get_text().strip().lower() for origins_str in self.origins_strs):
                    stop_page = page_num
                    break
            if start_page and stop_page:
                break
        else:
            stop_page = page_num

        for page_num, page in enumerate(list(extract_pages(pdf_path))[start_page:stop_page]):
            text_from_tables = []
            page_content = []
            table_num = 0
            first_element_flag = True
            table_extraction_flag = False
            pdf = pdfplumber.open(pdf_path)
            page_tables = pdf.pages[page_num]
            tables = page_tables.find_tables()

            page_elements = [(element.y1, element) for element in page._objs]
            page_elements.sort(key=lambda x: -x[0])

            lower_side, upper_side = 0, 0
            for i, component in enumerate(page_elements):
                element = component[1]

                if isinstance(element, LTTextContainer):
                    if not table_extraction_flag:
                        line_text, format_for_line = self._extract_text(element)
                        page_content.append(line_text)

                if isinstance(element, LTRect) and table_num < len(tables):
                    if first_element_flag:
                        lower_side = page.bbox[3] - tables[table_num].bbox[3]
                        upper_side = element.y1
                        table = self._extract_table(pdf_path, page_num, table_num)
                        table_string = self._table_converter(table)
                        text_from_tables.append(table_string)
                        page_content.append(table_string)
                        table_extraction_flag = True
                        first_element_flag = False
                    if element.y0 >= lower_side and element.y1 <= upper_side:
                        pass
                    elif i + 1 < len(page_elements) and not isinstance(page_elements[i + 1][1], LTRect):
                        table_extraction_flag = False
                        first_element_flag = True
                        table_num += 1
            pages.append(page_content)

        return ''.join(row for page in pages for row in page).replace('\0', '')

    @staticmethod
    def _extract_text(element):
        line_text = element.get_text()
        line_formats = []
        for text_line in element:
            if isinstance(text_line, LTTextContainer):
                for character in text_line:
                    if isinstance(character, LTChar):
                        line_formats.append(character.fontname)
                        line_formats.append(character.size)
        format_per_line = list(set(line_formats))

        return line_text, format_per_line

    @staticmethod
    def _extract_table(pdf_path, page_num, table_num):
        return pdfplumber.open(pdf_path).pages[page_num].extract_tables()[table_num]

    @staticmethod
    def _table_converter(table):
        table_string = ''
        for row_num in range(len(table)):
            row = table[row_num]
            cleansed_row = [
                item.replace('\n', '') if item is not None and '\n' in item else 'None' if item is None else item for
                item in row]
            table_string += f"|{'|'.join(cleansed_row)}|\n"
        return table_string[:-1]

    @staticmethod
    def clear_csv(csv_filename: str):
        open(csv_filename, 'w', encoding='utf-8').close()


if __name__ == '__main__':
    pdf_parser = PDFParser()
    pdf_parser.parse_files('../../../VKRsData')
