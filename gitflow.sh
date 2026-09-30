
# Get the current branch name
current_branch=$(git rev-parse --abbrev-ref HEAD)

# Function to check if the last command was successful
check_status() {
    if [ $? -ne 0 ]; then
        echo "Error: $1 failed"
        exit 1
    fi
}

# Push current branch changes
echo "Pushing changes to $current_branch..."
git push origin "$current_branch"
check_status "Push to $current_branch"

# Switch to develop and update
echo "Switching to develop branch..."
git checkout develop
check_status "Checkout develop"

echo "Pulling latest develop..."
git pull origin develop
check_status "Pull develop"

# Merge current branch into develop
echo "Merging $current_branch into develop..."
git merge "$current_branch"
check_status "Merge into develop"

echo "Pushing develop..."
git push origin develop
check_status "Push develop"

# Switch to main and update
echo "Switching to main branch..."
git checkout main
check_status "Checkout main"

echo "Pulling latest main..."
git pull origin main
check_status "Pull main"

# Merge develop into main
echo "Merging develop into main..."
git merge develop
check_status "Merge develop into main"

echo "Pushing main..."
git push origin main
check_status "Push main"

# Return to original branch
echo "Returning to $current_branch..."
git checkout "$current_branch"
check_status "Return to original branch"

echo "Git flow completed successfully!"

