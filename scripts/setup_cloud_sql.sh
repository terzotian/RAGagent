#!/bin/bash
set -e

# Configuration
REGION="asia-east1"
INSTANCE_NAME="rag-db-instance"
DB_NAME="lurag"
DB_USER="rag_admin"
PROJECT_ID=$(gcloud config get-value project)

echo "🚀 Starting Cloud SQL Setup for Project: $PROJECT_ID in $REGION..."

# 1. Enable Cloud SQL Admin API
echo "🔌 Enabling Cloud SQL Admin API..."
gcloud services enable sqladmin.googleapis.com

# 2. Create Cloud SQL Instance (PostgreSQL 15)
echo "🏗️ Creating Cloud SQL Instance '$INSTANCE_NAME' (this may take 5-10 minutes)..."
# Check if instance exists first to avoid error
if gcloud sql instances describe $INSTANCE_NAME --project=$PROJECT_ID &>/dev/null; then
    echo "✅ Instance '$INSTANCE_NAME' already exists."
else
    # Prompt for root password
    echo "🔑 Please enter a password for the 'postgres' (root) user:"
    read -s DB_ROOT_PASSWORD

    gcloud sql instances create $INSTANCE_NAME \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region=$REGION \
        --root-password=$DB_ROOT_PASSWORD \
        --storage-auto-increase
fi

# 3. Create Database
echo "🗄️ Creating Database '$DB_NAME'..."
if gcloud sql databases list --instance=$INSTANCE_NAME | grep -q $DB_NAME; then
    echo "✅ Database '$DB_NAME' already exists."
else
    gcloud sql databases create $DB_NAME --instance=$INSTANCE_NAME
fi

# 4. Create User
echo "👤 Creating User '$DB_USER'..."
if gcloud sql users list --instance=$INSTANCE_NAME | grep -q $DB_USER; then
    echo "✅ User '$DB_USER' already exists."
else
    echo "🔑 Please enter a password for the new user '$DB_USER':"
    read -s DB_USER_PASSWORD
    gcloud sql users create $DB_USER \
        --instance=$INSTANCE_NAME \
        --password=$DB_USER_PASSWORD
fi

# 5. Grant Permissions to Cloud Run Service Account
# Get the default Compute Engine service account which Cloud Run uses by default
SERVICE_ACCOUNT_EMAIL=$(gcloud iam service-accounts list --filter="displayName:Compute Engine default service account" --format="value(email)")

if [ -z "$SERVICE_ACCOUNT_EMAIL" ]; then
    echo "⚠️  Could not find default Compute Engine service account. Checking for specific Cloud Run SA..."
    # Fallback: try to find the one used in previous deployments or just warn user
    echo "⚠️  Please manually grant 'Cloud SQL Client' role to your Cloud Run service account."
else
    echo "🛡️ Granting 'Cloud SQL Client' role to $SERVICE_ACCOUNT_EMAIL..."
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
        --role="roles/cloudsql.client"
fi

# 6. Output Connection Info
CONNECTION_NAME=$(gcloud sql instances describe $INSTANCE_NAME --format="value(connectionName)")
echo ""
echo "✅ Cloud SQL Setup Complete!"
echo "------------------------------------------------"
echo "Instance Connection Name: $CONNECTION_NAME"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "------------------------------------------------"
echo "📋 To deploy Cloud Run with this DB, run:"
echo ""
echo "gcloud run deploy rag-backend \\"
echo "  --image gcr.io/$PROJECT_ID/rag-backend:latest \\"
echo "  --add-cloudsql-instances $CONNECTION_NAME \\"
echo "  --set-env-vars DATABASE_URL=\"postgresql+psycopg2://$DB_USER:<PASSWORD>@/$DB_NAME?host=/cloudsql/$CONNECTION_NAME\" \\"
echo "  --set-env-vars VERTEX_PROJECT_ID=<YOUR_GCP_PROJECT_ID> \\"
echo "  --set-env-vars VERTEX_LOCATION=$REGION \\"
echo "  --region $REGION"
echo ""
