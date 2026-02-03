import { getCountries, getCountryCallingCode } from 'libphonenumber-js/mobile';
import countries from 'i18n-iso-countries';
import enLocale from 'i18n-iso-countries/langs/en.json';

countries.registerLocale(enLocale);

export interface CountryCode {
  code: string;
  dialCode: string;
  name: string;
}

export const COUNTRY_CODES: CountryCode[] = getCountries()
  .map((countryCode) => {
    const name = countries.getName(countryCode, 'en') || countryCode;
    let dialCode: string;
    try {
      dialCode = `+${getCountryCallingCode(countryCode)}`;
    } catch {
      dialCode = '';
    }
    return {
      code: countryCode,
      dialCode,
      name,
    };
  })
  .filter((country) => country.dialCode !== '')
  .sort((a, b) => a.name.localeCompare(b.name));

export const COUNTRIES_LIST: string[] = COUNTRY_CODES.map((c) => c.name);
