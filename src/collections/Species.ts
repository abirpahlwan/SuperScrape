import type { CollectionConfig } from 'payload'

export const Species: CollectionConfig = {
  slug: 'species',
  admin: {
    useAsTitle: 'id',
  },
  fields: [
    { name: 'image_urls', type: 'json' },
    { name: 'taxonomy', type: 'json' },
    { name: 'names', type: 'json' },
    { name: 'description', type: 'json' },
    { name: 'morphology', type: 'json' },
    { name: 'ecology', type: 'json' },
    { name: 'phenology', type: 'json' },
    { name: 'reproduction', type: 'json' },
    { name: 'economic_importance', type: 'json' },
    { name: 'specimen_data', type: 'json' },
    { name: 'media_summary', type: 'json' },
    { name: 'metadata', type: 'json' },
  ],
}
