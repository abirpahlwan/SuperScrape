import type { CollectionConfig } from 'payload'

function extractCommonName(data: Record<string, unknown>): string {
  const names = data?.names as Record<string, unknown> | undefined
  const commonNames = names?.common_names as { name?: string }[] | undefined
  return commonNames?.[0]?.name || (names?.scientific_name as string) || ''
}

export const Species: CollectionConfig = {
  slug: 'species',
  admin: {
    useAsTitle: 'species_name',
  },
  fields: [
    {
      name: 'species_name',
      type: 'text',
      admin: { hidden: true },
      hooks: {
        beforeChange: [
          ({ data }) => {
            if (data) {
              return extractCommonName(data)
            }
          },
        ],
      },
    },
    {
      name: 'source_url',
      type: 'text',
      required: true,
      unique: true,
      index: true,
      admin: {
        readOnly: true,
      },
    },
    {
      name: 'raw_markdown',
      type: 'textarea',
      admin: {
        readOnly: true,
      },
    },
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
