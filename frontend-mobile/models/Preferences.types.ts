export interface Preference {
    id: number,
    name: string
}

export interface PreferencesResponse extends Preference{
    picture: string
}