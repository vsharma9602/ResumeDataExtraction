from dateutil.parser import parse
from tabula import read_pdf
import pandas as pd
import subprocess


def is_date(string, fuzzy=False):
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try: 
        parse(string, fuzzy=fuzzy)
        return True

    except ValueError:
        return False
    except:
        return False



abc = '2018|'

print(abc.replace('|',''))


'''
try:
    df = read_pdf('resumes/SgLMYBnaXs.pdf')
    if df == None:
        df = pd.DataFrame()
except pd.errors.ParserError:
    print('continue')
    df = pd.DataFrame()
except subprocess.CalledProcessError:
    print('continue docx Found')
    df = pd.DataFrame()
except:
    df = read_pdf('resumes/Amey Bhandare.pdf')
    print('continue1')


print(df)
'''
