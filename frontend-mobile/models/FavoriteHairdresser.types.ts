import { HairdresserResponse } from './Hairdresser.types';

/** An item of `GET /api/customers/me/favorite-hairdressers`: the public hairdresser format, without the CNPJ. */
export type FavoriteHairdresser = Pick<HairdresserResponse, 'id' | 'user' | 'resume'>;
