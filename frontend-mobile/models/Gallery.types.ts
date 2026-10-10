/** An item of `GET /api/hairdressers/{id}/gallery-photos`: `image` is the public URL of the stored WebP. */
export interface GalleryPhoto {
    id: number;
    image: string;
    created_at: string;
}

/** A hairdresser keeps at most this many photos in the gallery. */
export const GALLERY_MAX_PHOTOS = 30;
