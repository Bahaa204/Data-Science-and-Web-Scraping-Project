import pandas as pd
import numpy as np
import os
import shutil

# ============================================
# CHECK AND RESTORE ORIGINAL FILES IF MISSING
# ============================================
def ensure_original_file(file_path, backup_folder='original_data'):
    if os.path.exists(file_path):
        return True
    backup_path = os.path.join(backup_folder, os.path.basename(file_path))
    if os.path.exists(backup_path):
        print(f"Restoring {file_path} from {backup_folder}...")
        shutil.copy2(backup_path, file_path)
        return True
    return False

required_originals = [
    'all_platforms_latest.csv',
    'Hourly_Rate.csv',
    'steam_games_dataset.csv',
    'currencies.csv'
]

for f in required_originals:
    if not ensure_original_file(f):
        print(f"❌ ERROR: {f} not found and no backup available.")
        exit(1)

# ============================================
# FILE PATHS
# ============================================
SUBS_ORIGINAL    = 'all_platforms_latest.csv'
SUBS_CLEANED     = 'subscriptions_cleaned.csv'
HOURLY_IN        = 'Hourly_Rate.csv'
HOURLY_OUT       = 'hourly_wage_cleaned.csv'
STEAM_IN         = 'steam_games_dataset.csv'
STEAM_OUT        = 'steam_games_cleaned.csv'
CURRENCIES_ORIGINAL = 'currencies.csv'
CURRENCIES_CLEAN    = 'currencies_cleaned.csv'
COMBINED_FILE    = 'all_clean_data_combined.xlsx'

EXCHANGE_RATES = {
    'USD': 1.0,    'LKR': 300.0,   'IDR': 15500.0, 'TWD': 32.0,    'HKD': 7.8,
    'PHP': 56.0,   'JPY': 158.77,  'EUR': 0.87,    'GBP': 0.75,    'KRW': 1350.0,
    'MYR': 4.7,    'THB': 35.0,    'VND': 25000.0, 'AED': 3.67,    'SAR': 3.75,
    'EGP': 48.0,   'KWD': 0.31,    'BHD': 0.38,    'OMR': 0.38,    'QAR': 3.64,
    'JOD': 0.71,   'LBP': 15000.0, 'TND': 3.1,     'DZD': 135.0,   'MAD': 10.0,
    'NGN': 1500.0, 'KES': 130.0,   'PKR': 280.0,   'BDT': 110.0,   'NPR': 133.0,
    'UAH': 38.0,   'KZT': 450.0,   'UZS': 12500.0, 'GEL': 2.7,     'AZN': 1.7,
    'AMD': 390.0,  'BYN': 3.3,     'MDL': 18.0,    'KGS': 88.0,    'TJS': 10.8,
    'AUD': 1.43,   'CAD': 1.37,    'NZD': 1.71,    'CHF': 0.79,    'SEK': 9.36,
    'NOK': 9.72,   'DKK': 6.47,    'PLN': 3.68,    'CZK': 21.17,   'HUF': 337.85,
    'RON': 4.41,   'BGN': 1.70,    'HRK': 6.80,    'RSD': 110.0,   'ISK': 124.98,
}

# ============================================
# 1. CLEAN SUBSCRIPTIONS
# ============================================
print("Loading subscriptions...")
subs = pd.read_csv(SUBS_ORIGINAL)

def clean_price_string(val):
    if pd.isna(val) or val == '':
        return np.nan
    s = str(val).strip()
    for sym in ['US$', '$', 'AED', 'EGP', 'SAR', 'KR', '₪', '€', '£', '¥', '₱', 'RM', 'Rp', '₹', 'LKR', 'IDR', 'TWD', 'HKD']:
        s = s.replace(sym, '')
    if ',' in s and '.' not in s:
        parts = s.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = s.replace(',', '.')
    s = ''.join(c for c in s if c.isdigit() or c == '.')
    try:
        return float(s)
    except:
        return np.nan

def get_currency_code(row):
    curr = str(row['currency']).strip()
    mapping = {
        'US$': 'USD', '$': 'USD', 'AED': 'AED', 'EGP': 'EGP',
        'SAR': 'SAR', 'KR': 'KRW', '₪': 'ILS', '€': 'EUR',
        '£': 'GBP', '¥': 'JPY', '₱': 'PHP', 'RM': 'MYR',
        'Rp': 'IDR', '₹': 'INR', 'LKR': 'LKR', 'IDR': 'IDR',
        'TWD': 'TWD', 'HKD': 'HKD'
    }
    return mapping.get(curr, curr)

def convert_to_usd(row):
    price = row['price_local']
    curr  = row['currency_code']
    if pd.isna(price):
        return np.nan
    if curr == 'USD':
        return price
    rate = EXCHANGE_RATES.get(curr)
    return price / rate if rate else np.nan

subs['price_local']    = subs['price'].apply(clean_price_string)
subs['currency_code']  = subs.apply(get_currency_code, axis=1)

shahid = (subs['platform'] == 'Shahid') & (subs['plan_type'] == 'General')
subs.loc[shahid, 'price_local']   = 0.0
subs.loc[shahid, 'currency_code'] = 'USD'

subs['price_usd'] = subs.apply(convert_to_usd, axis=1)

overrides = {
    ('Sri Lanka',  'Duo'):               969   / 300,
    ('Sri Lanka',  'Family'):            1260  / 300,
    ('Indonesia',  'Apple TV+ Monthly'): 99000 / 15500,
    ('Taiwan',     'Apple TV+ Monthly'): 250   / 32,
    ('Hong Kong',  'Duo'):               98    / 7.8,
    ('Hong Kong',  'Family'):            128   / 7.8,
    ('Hong Kong',  'Apple TV+ Monthly'): 68    / 7.8,
}
for (region, plan), usd_val in overrides.items():
    mask = (subs['region'] == region) & (subs['plan_type'] == plan)
    subs.loc[mask, 'price_usd'] = usd_val

sweden_mask = (subs['platform'] == 'Apple TV+') & (subs['region'] == 'Sweden') & (subs['plan_type'] == 'Apple TV+ Monthly')
if sweden_mask.any():
    subs.loc[sweden_mask, 'price_usd'] = 99 / 9.36
    print(f"Fixed {sweden_mask.sum()} row(s) for Apple TV+ Sweden.")
else:
    print("Apple TV+ Sweden row not found.")

subs['price_usd'] = subs['price_usd'].round(2)
subs_clean = subs.dropna(subset=['price_usd']).copy()
subs_clean = subs_clean[['platform', 'region', 'plan_type', 'price_usd', 'scraped_at']]
subs_clean.rename(columns={'price_usd': 'price'}, inplace=True)
subs_clean['currency'] = 'USD'
subs_clean.to_csv(SUBS_CLEANED, index=False)
print(f"✅ Subscriptions saved to {SUBS_CLEANED}")

# ============================================
# 2. CLEAN HOURLY WAGES
# ============================================
print("\nLoading hourly wages...")
hourly = pd.read_csv(HOURLY_IN)
hourly.columns = ['country_code', 'hourly_wage_usd'] + list(hourly.columns[2:]) if hourly.shape[1] > 2 else ['country_code', 'hourly_wage_usd']
hourly = hourly[['country_code', 'hourly_wage_usd']].copy()
hourly['hourly_wage_usd'] = pd.to_numeric(hourly['hourly_wage_usd'].astype(str).str.replace('$', '').str.strip(), errors='coerce')
hourly = hourly.dropna(subset=['country_code', 'hourly_wage_usd'])
hourly = hourly[hourly['hourly_wage_usd'] > 0]
hourly['hourly_wage_usd'] = hourly['hourly_wage_usd'].round(2)

country_names = {
    'ABW': 'Aruba', 'AFG': 'Afghanistan', 'AGO': 'Angola', 'ALB': 'Albania',
    'AND': 'Andorra', 'ARE': 'United Arab Emirates', 'ARG': 'Argentina', 'ARM': 'Armenia',
    'ASM': 'American Samoa', 'ATG': 'Antigua and Barbuda', 'AUS': 'Australia', 'AUT': 'Austria',
    'AZE': 'Azerbaijan', 'BDI': 'Burundi', 'BEL': 'Belgium', 'BEN': 'Benin',
    'BFA': 'Burkina Faso', 'BGD': 'Bangladesh', 'BGR': 'Bulgaria', 'BHR': 'Bahrain',
    'BHS': 'Bahamas', 'BIH': 'Bosnia and Herzegovina', 'BLR': 'Belarus', 'BLZ': 'Belize',
    'BMU': 'Bermuda', 'BOL': 'Bolivia', 'BRA': 'Brazil', 'BRB': 'Barbados',
    'BRN': 'Brunei', 'BTN': 'Bhutan', 'BWA': 'Botswana', 'CAF': 'Central African Republic',
    'CAN': 'Canada', 'CHE': 'Switzerland', 'CHL': 'Chile', 'CHN': 'China',
    'CIV': "Côte d'Ivoire", 'CMR': 'Cameroon', 'COD': 'Democratic Republic of the Congo',
    'COG': 'Republic of the Congo', 'COL': 'Colombia', 'COM': 'Comoros', 'CPV': 'Cape Verde',
    'CRI': 'Costa Rica', 'CUB': 'Cuba', 'CUW': 'Curaçao', 'CYM': 'Cayman Islands',
    'CYP': 'Cyprus', 'CZE': 'Czech Republic', 'DEU': 'Germany', 'DJI': 'Djibouti',
    'DMA': 'Dominica', 'DNK': 'Denmark', 'DOM': 'Dominican Republic', 'DZA': 'Algeria',
    'ECU': 'Ecuador', 'EGY': 'Egypt', 'ERI': 'Eritrea', 'ESP': 'Spain',
    'EST': 'Estonia', 'ETH': 'Ethiopia', 'FIN': 'Finland', 'FJI': 'Fiji',
    'FLK': 'Falkland Islands', 'FRA': 'France', 'FRO': 'Faroe Islands', 'FSM': 'Micronesia',
    'GAB': 'Gabon', 'GBR': 'United Kingdom', 'GEO': 'Georgia', 'GGY': 'Guernsey',
    'GHA': 'Ghana', 'GIB': 'Gibraltar', 'GIN': 'Guinea', 'GMB': 'Gambia',
    'GNB': 'Guinea-Bissau', 'GNQ': 'Equatorial Guinea', 'GRC': 'Greece', 'GRD': 'Grenada',
    'GRL': 'Greenland', 'GTM': 'Guatemala', 'GUM': 'Guam', 'GUY': 'Guyana',
    'HKG': 'Hong Kong', 'HND': 'Honduras', 'HRV': 'Croatia', 'HTI': 'Haiti',
    'HUN': 'Hungary', 'IDN': 'Indonesia', 'IMN': 'Isle of Man', 'IND': 'India',
    'IRL': 'Ireland', 'IRN': 'Iran', 'IRQ': 'Iraq', 'ISL': 'Iceland',
    'ISR': 'Israel', 'ITA': 'Italy', 'JAM': 'Jamaica', 'JEY': 'Jersey',
    'JOR': 'Jordan', 'JPN': 'Japan', 'KAZ': 'Kazakhstan', 'KEN': 'Kenya',
    'KGZ': 'Kyrgyzstan', 'KHM': 'Cambodia', 'KIR': 'Kiribati', 'KNA': 'Saint Kitts and Nevis',
    'KOR': 'South Korea', 'KWT': 'Kuwait', 'LAO': 'Laos', 'LBN': 'Lebanon',
    'LBR': 'Liberia', 'LBY': 'Libya', 'LCA': 'Saint Lucia', 'LIE': 'Liechtenstein',
    'LKA': 'Sri Lanka', 'LSO': 'Lesotho', 'LTU': 'Lithuania', 'LUX': 'Luxembourg',
    'LVA': 'Latvia', 'MAC': 'Macao', 'MAF': 'Saint Martin', 'MAR': 'Morocco',
    'MCO': 'Monaco', 'MDA': 'Moldova', 'MDG': 'Madagascar', 'MDV': 'Maldives',
    'MEX': 'Mexico', 'MHL': 'Marshall Islands', 'MKD': 'North Macedonia', 'MLI': 'Mali',
    'MLT': 'Malta', 'MMR': 'Myanmar', 'MNE': 'Montenegro', 'MNG': 'Mongolia',
    'MNP': 'Northern Mariana Islands', 'MOZ': 'Mozambique', 'MRT': 'Mauritania',
    'MSR': 'Montserrat', 'MTQ': 'Martinique', 'MUS': 'Mauritius', 'MWI': 'Malawi',
    'MYS': 'Malaysia', 'MYT': 'Mayotte', 'NAM': 'Namibia', 'NCL': 'New Caledonia',
    'NER': 'Niger', 'NFK': 'Norfolk Island', 'NGA': 'Nigeria', 'NIC': 'Nicaragua',
    'NIU': 'Niue', 'NLD': 'Netherlands', 'NOR': 'Norway', 'NPL': 'Nepal',
    'NRU': 'Nauru', 'NZL': 'New Zealand', 'OMN': 'Oman', 'PAK': 'Pakistan',
    'PAN': 'Panama', 'PCN': 'Pitcairn', 'PER': 'Peru', 'PHL': 'Philippines',
    'PLW': 'Palau', 'PNG': 'Papua New Guinea', 'POL': 'Poland', 'PRI': 'Puerto Rico',
    'PRK': 'North Korea', 'PRT': 'Portugal', 'PRY': 'Paraguay', 'PSE': 'Palestine',
    'PYF': 'French Polynesia', 'QAT': 'Qatar', 'REU': 'Réunion', 'ROU': 'Romania',
    'RUS': 'Russia', 'RWA': 'Rwanda', 'SAU': 'Saudi Arabia', 'SDN': 'Sudan',
    'SEN': 'Senegal', 'SGP': 'Singapore', 'SGS': 'South Georgia', 'SHN': 'Saint Helena',
    'SJM': 'Svalbard and Jan Mayen', 'SLB': 'Solomon Islands', 'SLE': 'Sierra Leone',
    'SLV': 'El Salvador', 'SMR': 'San Marino', 'SOM': 'Somalia', 'SPM': 'Saint Pierre and Miquelon',
    'SRB': 'Serbia', 'SSD': 'South Sudan', 'STP': 'Sao Tome and Principe', 'SUR': 'Suriname',
    'SVK': 'Slovakia', 'SVN': 'Slovenia', 'SWE': 'Sweden', 'SWZ': 'Eswatini',
    'SXM': 'Sint Maarten', 'SYC': 'Seychelles', 'SYR': 'Syria', 'TCA': 'Turks and Caicos Islands',
    'TCD': 'Chad', 'TGO': 'Togo', 'THA': 'Thailand', 'TJK': 'Tajikistan',
    'TKL': 'Tokelau', 'TKM': 'Turkmenistan', 'TLS': 'Timor-Leste', 'TON': 'Tonga',
    'TTO': 'Trinidad and Tobago', 'TUN': 'Tunisia', 'TUR': 'Turkey', 'TUV': 'Tuvalu',
    'TWN': 'Taiwan', 'TZA': 'Tanzania', 'UGA': 'Uganda', 'UKR': 'Ukraine',
    'UMI': 'United States Minor Outlying Islands', 'URY': 'Uruguay', 'USA': 'United States',
    'UZB': 'Uzbekistan', 'VAT': 'Vatican City', 'VCT': 'Saint Vincent and the Grenadines',
    'VEN': 'Venezuela', 'VGB': 'British Virgin Islands', 'VIR': 'United States Virgin Islands',
    'VNM': 'Vietnam', 'VUT': 'Vanuatu', 'WLF': 'Wallis and Futuna', 'WSM': 'Samoa',
    'XKX': 'Kosovo', 'YEM': 'Yemen', 'ZAF': 'South Africa', 'ZMB': 'Zambia', 'ZWE': 'Zimbabwe',
    'AFE': 'Africa Eastern', 'AFW': 'Africa Western', 'AFR': 'Africa',
    'ARB': 'Arab World', 'BEA': 'Benin', 'BEC': 'Belgium', 'BHI': 'Bahrain',
    'BLA': 'Bolivia', 'BMN': 'Bermuda', 'BSS': 'South Sudan', 'CAA': 'Canada',
    'CEA': 'Central Europe', 'CEB': 'Central Europe and Baltics', 'CEU': 'European Union',
    'CLA': 'Chile', 'CME': 'Cameroon', 'CSA': 'Czech Republic', 'CSS': 'Czech Republic',
    'DEA': 'Germany', 'DEC': 'Germany', 'DLA': 'Dominica', 'DMN': 'Dominican Republic',
    'DNS': 'Denmark', 'DSA': 'Dominica', 'DSF': 'Dominican Republic', 'DSS': 'Dominican Republic',
    'EAP': 'East Asia & Pacific', 'EAR': 'Early', 'EAS': 'East Asia', 'ECA': 'Europe & Central Asia',
    'ECS': 'Ecuador', 'EMU': 'Euro area', 'EUU': 'European Union', 'FCS': 'Fragile and Conflict Affected States',
    'FXS': 'France', 'HIC': 'High income', 'HPC': 'High income',
    'IBB': 'IBRD', 'IBD': 'IBRD', 'IBT': 'IBRD', 'IDA': 'IDA', 'IDB': 'IDA',
    'IDX': 'IDA', 'INX': 'India', 'LAC': 'Latin America & Caribbean', 'LCN': 'Latin America',
    'LDC': 'Least developed countries', 'LIC': 'Low income', 'LMC': 'Lower middle income',
    'LMY': 'Lower middle income', 'LTE': 'Lithuania', 'MDE': 'Moldova', 'MEA': 'Middle East & North Africa',
    'MIC': 'Middle income', 'MNA': 'Middle East & North Africa', 'NAC': 'North America',
    'NAF': 'North Africa', 'NRS': 'Nepal', 'NXS': 'Netherlands', 'OED': 'OECD members',
    'OSS': 'Other small states', 'PRE': 'Pre', 'PSS': 'Pacific Island small states',
    'PST': 'Pacific Island small states', 'RRS': 'Russia', 'SAS': 'South Asia',
    'SSA': 'Sub-Saharan Africa', 'SSF': 'Sub-Saharan Africa', 'SST': 'Small states',
    'SXZ': 'Sint Maarten', 'TEA': 'Turkey', 'TEC': 'Turkey', 'TLA': 'Timor-Leste',
    'TMN': 'Turkmenistan', 'TSA': 'Tonga', 'TSS': 'Tonga', 'UMC': 'Upper middle income',
    'WLD': 'World', 'XZN': 'Zambia'
}

hourly['country_name'] = hourly['country_code'].map(country_names)
before = len(hourly)
hourly = hourly.dropna(subset=['country_name'])
print(f"Removed {before - len(hourly)} rows with unknown country codes.")
hourly.to_csv(HOURLY_OUT, index=False)
print(f"✅ Hourly wages saved to {HOURLY_OUT}")

# ============================================
# 3. CLEAN STEAM GAMES
# ============================================
print("\nLoading Steam games...")
steam = pd.read_csv(STEAM_IN, encoding='utf-8-sig')

steam = steam.dropna(subset=['Title'])
steam = steam[steam['Title'].astype(str).str.strip() != '']
print(f"Removed rows with missing titles. Remaining rows: {len(steam)}")

steam['Title'] = steam['Title'].astype(str).str.replace('â„¢', '', regex=False)
steam['Title'] = steam['Title'].astype(str).str.replace('Â', '', regex=False)
steam['Title'] = steam['Title'].str.strip()
steam['Title'] = steam['Title'].astype(str).str.encode('ascii', 'ignore').str.decode('ascii')

def clean_price_to_usd(price_str, region):
    if pd.isna(price_str) or price_str == '':
        return np.nan
    s = str(price_str).strip()
    currency = None
    if '€' in s:
        currency = 'EUR'
    elif '£' in s:
        currency = 'GBP'
    elif '¥' in s:
        currency = 'CNY' if region == 'CN' else 'JPY'
    elif 'R$' in s:
        currency = 'BRL'
    elif '₹' in s:
        currency = 'INR'
    elif '$' in s:
        non_usd = {'CA': 'CAD', 'AU': 'AUD', 'NZ': 'NZD', 'HK': 'HKD', 'SG': 'SGD', 'TW': 'TWD', 'MX': 'MXN'}
        currency = non_usd.get(region, 'USD')
    else:
        region_default = {
            'TR': 'TRY', 'CN': 'CNY', 'DE': 'EUR', 'GB': 'GBP',
            'BR': 'BRL', 'IN': 'INR', 'JP': 'JPY', 'KR': 'KRW',
            'ID': 'IDR', 'MY': 'MYR', 'PH': 'PHP', 'TH': 'THB',
            'VN': 'VND', 'AE': 'AED', 'SA': 'SAR', 'EG': 'EGP',
            'KW': 'KWD', 'BH': 'BHD', 'OM': 'OMR', 'QA': 'QAR',
            'JO': 'JOD', 'LB': 'LBP', 'TN': 'TND', 'DZ': 'DZD',
            'MA': 'MAD', 'NG': 'NGN', 'KE': 'KES', 'PK': 'PKR',
            'BD': 'BDT', 'LK': 'LKR', 'NP': 'NPR', 'UA': 'UAH',
            'KZ': 'KZT', 'UZ': 'UZS', 'GE': 'GEL', 'AZ': 'AZN',
            'AM': 'AMD', 'BY': 'BYN', 'MD': 'MDL', 'KG': 'KGS',
            'TJ': 'TJS', 'AU': 'AUD', 'CA': 'CAD', 'NZ': 'NZD',
            'CH': 'CHF', 'SE': 'SEK', 'NO': 'NOK', 'DK': 'DKK',
            'PL': 'PLN', 'CZ': 'CZK', 'HU': 'HUF', 'RO': 'RON',
            'BG': 'BGN', 'HR': 'HRK', 'RS': 'RSD', 'IS': 'ISK'
        }
        currency = region_default.get(region, 'USD')
    for sym in ['€', '£', '¥', 'R$', '₹', '$']:
        s = s.replace(sym, '')
    if ',' in s and '.' not in s:
        parts = s.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = s.replace(',', '.')
    s = ''.join(c for c in s if c.isdigit() or c == '.')
    try:
        price_num = float(s)
    except:
        return np.nan
    if currency == 'USD':
        return price_num
    rate = EXCHANGE_RATES.get(currency)
    return price_num / rate if rate else np.nan

steam['Current Price']  = steam.apply(lambda row: clean_price_to_usd(row['Current Price'], row['Region']), axis=1)
steam['Original Price'] = steam.apply(lambda row: clean_price_to_usd(row['Original Price'], row['Region']), axis=1)
steam['Current Price']  = steam['Current Price'].round(2)
steam['Original Price'] = steam['Original Price'].round(2)
steam['Discount']       = pd.to_numeric(steam['Discount'].astype(str).str.replace('%', '').str.strip(), errors='coerce').fillna(0)
steam['currency']       = 'USD'
steam = steam.dropna(subset=['Current Price'])
steam.to_csv(STEAM_OUT, index=False)
print(f"✅ Steam games saved to {STEAM_OUT}")

# ============================================
# 4. CLEAN CURRENCIES
# ============================================
if os.path.exists(CURRENCIES_ORIGINAL):
    df_curr = pd.read_csv(CURRENCIES_ORIGINAL)
    df_long = df_curr.melt(var_name='currency_code', value_name='exchange_rate') if df_curr.shape[0] == 1 else df_curr.copy()
    if 'currency_code' not in df_long.columns:
        df_long = df_long.iloc[:, :2]
        df_long.columns = ['currency_code', 'exchange_rate']
    df_long['exchange_rate'] = pd.to_numeric(df_long['exchange_rate'], errors='coerce').round(2)
    df_long = df_long.dropna(subset=['exchange_rate'])
    df_long = df_long[df_long['exchange_rate'] != 0].drop_duplicates(subset=['currency_code'])
    if 'USD' not in df_long['currency_code'].values:
        df_long = pd.concat([pd.DataFrame({'currency_code': ['USD'], 'exchange_rate': [1.0]}), df_long], ignore_index=True)
    df_long.to_csv(CURRENCIES_CLEAN, index=False)
    print(f"✅ Currencies saved to {CURRENCIES_CLEAN}")
else:
    clean_df = pd.DataFrame([{'currency_code': c, 'exchange_rate': round(r, 2)} for c, r in EXCHANGE_RATES.items()])
    clean_df.to_csv(CURRENCIES_CLEAN, index=False)
    print(f"✅ Currencies built from internal rates and saved to {CURRENCIES_CLEAN}")

# ============================================
# 5. COMBINE DATASETS - SIDE BY SIDE
# ============================================
print("\nCombining datasets side by side...")

subs  = pd.read_csv(SUBS_CLEANED)
steam = pd.read_csv(STEAM_OUT)

subs.columns  = subs.columns.str.strip().str.lower().str.replace(' ', '_')
steam.columns = steam.columns.str.strip().str.lower().str.replace(' ', '_')

def get_col(df, *candidates):
    for c in candidates:
        if c in df.columns:
            return df[c]
    raise KeyError(f"None of {candidates} found in columns: {df.columns.tolist()}")

subs_final = pd.DataFrame({
    'sub_source':    'Subscriptions',
    'sub_type':      'subscription_plan',
    'sub_name':      subs['plan_type'],
    'sub_region':    subs['region'],
    'sub_platform':  subs['platform'],
    'sub_price_usd': subs['price'],
    'sub_currency':  subs['currency'] if 'currency' in subs.columns else 'USD',
    'sub_date':      subs['scraped_at'],
}).reset_index(drop=True)

steam_final = pd.DataFrame({
    'steam_source':             'Steam',
    'steam_type':               'game',
    'steam_name':               get_col(steam, 'title'),
    'steam_region':             get_col(steam, 'region'),
    'steam_platform':           get_col(steam, 'platform', 'platforms'),
    'steam_price_usd':          get_col(steam, 'current_price'),
    'steam_original_price_usd': get_col(steam, 'original_price'),
    'steam_discount_percent':   get_col(steam, 'discount'),
    'steam_currency':           steam['currency'] if 'currency' in steam.columns else 'USD',
    'steam_date':               get_col(steam, 'scraped_at'),
}).reset_index(drop=True)

combined = pd.concat([steam_final, subs_final], axis=1)

print(f"Steam rows:        {combined['steam_source'].notna().sum()}")
print(f"Subscription rows: {combined['sub_source'].notna().sum()}")
print(f"Combined shape:    {combined.shape}")

combined.to_excel(COMBINED_FILE, index=False)
print(f"✅ Combined dataset saved as: {COMBINED_FILE}")
print(f"   Steam data:        columns A-J")
print(f"   Subscription data: columns K onwards")

# ============================================
# 6. ORGANISE FILES INTO FOLDERS
# ============================================
print("\nOrganising files into folders...")

os.makedirs('original_data', exist_ok=True)
os.makedirs('clean_data',    exist_ok=True)

original_files = ['all_platforms_latest.csv', 'Hourly_Rate.csv', 'steam_games_dataset.csv', 'currencies.csv']
cleaned_files  = [SUBS_CLEANED, HOURLY_OUT, STEAM_OUT, CURRENCIES_CLEAN]

for file in original_files:
    if os.path.exists(file):
        shutil.move(file, os.path.join('original_data', file))
        print(f"Moved: {file} -> original_data/")
    else:
        print(f"Not found (already moved): {file}")

for file in cleaned_files + [COMBINED_FILE]:
    if os.path.exists(file):
        shutil.move(file, os.path.join('clean_data', file))
        print(f"Moved: {file} -> clean_data/")
    else:
        print(f"Not found: {file}")

print("\n✅ Done. Originals in 'original_data/', cleaned files in 'clean_data/'")