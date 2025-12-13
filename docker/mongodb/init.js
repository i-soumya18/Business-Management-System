// MongoDB Initialization Script
// This script sets up the product catalog database

db = db.getSiblingDB('bms_catalog');

// Create collections
db.createCollection('products');
db.createCollection('categories');
db.createCollection('product_images');
db.createCollection('product_variants');

// Create indexes for products
db.products.createIndex({ sku: 1 }, { unique: true });
db.products.createIndex({ name: 'text', description: 'text' });
db.products.createIndex({ category_id: 1 });
db.products.createIndex({ status: 1 });
db.products.createIndex({ created_at: -1 });

// Create indexes for categories
db.categories.createIndex({ slug: 1 }, { unique: true });
db.categories.createIndex({ parent_id: 1 });

// Create indexes for product_variants
db.product_variants.createIndex({ product_id: 1 });
db.product_variants.createIndex({ sku: 1 }, { unique: true });
db.product_variants.createIndex({ 'attributes.size': 1 });
db.product_variants.createIndex({ 'attributes.color': 1 });

// Create indexes for product_images
db.product_images.createIndex({ product_id: 1 });
db.product_images.createIndex({ is_primary: 1 });

// Insert sample category structure
db.categories.insertMany([
  {
    _id: ObjectId(),
    name: 'Men',
    slug: 'men',
    description: 'Men\'s clothing',
    parent_id: null,
    image_url: null,
    is_active: true,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    _id: ObjectId(),
    name: 'Women',
    slug: 'women',
    description: 'Women\'s clothing',
    parent_id: null,
    image_url: null,
    is_active: true,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    _id: ObjectId(),
    name: 'Kids',
    slug: 'kids',
    description: 'Kids\' clothing',
    parent_id: null,
    image_url: null,
    is_active: true,
    created_at: new Date(),
    updated_at: new Date()
  }
]);

print('MongoDB initialized successfully!');
