# Yuba Profile Save Draft API

## Endpoint

```
POST /profiles/me/save-draft
```

Save a draft Yuba Profile with optional profile picture upload.

## Authentication

Requires Bearer token in Authorization header.

## Request Format

**Content-Type:** `multipart/form-data`

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | String (JSON) | Yes | Profile data as JSON string |
| `profile_picture` | File | No | Profile picture image file |

### Profile Picture Requirements

- **Allowed formats:** JPG, JPEG, PNG, GIF, WEBP, BMP
- **Max file size:** 5 MB
- **Recommended:** Square images, min 400x400px

## Request Examples

### JavaScript (Fetch API)

```javascript
const profileData = {
  first_name: "John",
  last_name: "Doe",
  gender: "Male",
  date_of_birth: "1990-01-15",
  email: "john@example.com",
  country: "United States",
  linkedin_url: "https://linkedin.com/in/johndoe",
  website_url: "https://johndoe.com",
  education: ["Bachelor of Science in Computer Science"],
  employment_history: [
    {
      organization: "Tech Corp",
      role_title: "Software Engineer",
      start_date: "2020-01",
      end_date: "Present",
      responsibilities_description: "Developed web applications"
    }
  ],
  achievement: "Built a successful SaaS product",
  personal_statement: "Passionate entrepreneur looking for a technical co-founder",
  social_links: {
    twitter: "https://twitter.com/johndoe",
    github: "https://github.com/johndoe"
  },
  professional_background: "Software Development",
  industries_of_interest: ["SaaS", "FinTech"],
  responsibilities_offered: ["CTO", "Technical Leadership"],
  skills_needed: ["Product Management", "Marketing"],
  preferred_languages: [
    { language_id: "en", importance: "must_have" },
    { language_id: "es", importance: "nice_to_have" }
  ],
  preferred_country: "United States",
  preferred_country_importance: "nice_to_have",
  expected_commitment: "Full-time",
  preferred_commitment: "Full-time",
  commitment_importance: "must_have",
  venture_stage: ["Idea"],
  preferred_venture_stage: ["Idea", "Prototype"],
  age_enabled: true,
  age_min: 25,
  age_max: 45,
  age_importance: "nice_to_have"
};

const formData = new FormData();

// Add profile data as JSON string
formData.append("data", JSON.stringify(profileData));

// Add profile picture if selected
const fileInput = document.querySelector('input[type="file"]');
if (fileInput?.files[0]) {
  formData.append("profile_picture", fileInput.files[0]);
}

// Send request
const response = await fetch("/profiles/me/save-draft", {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${yourAuthToken}`
  },
  body: formData
});

const result = await response.json();
console.log(result);
```

### React Example

```jsx
const handleSaveDraft = async (profileData, profilePicture) => {
  const formData = new FormData();

  // Add profile data
  formData.append("data", JSON.stringify(profileData));

  // Add profile picture if exists
  if (profilePicture) {
    formData.append("profile_picture", profilePicture);
  }

  try {
    const response = await fetch("/profiles/me/save-draft", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`
      },
      body: formData
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail);
    }

    const savedProfile = await response.json();
    console.log("Profile saved:", savedProfile);
    return savedProfile;
  } catch (error) {
    console.error("Failed to save profile:", error.message);
    throw error;
  }
};
```

### cURL Example

```bash
curl -X POST "https://api.example.com/profiles/me/save-draft" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -F "data={\"first_name\":\"John\",\"last_name\":\"Doe\",\"gender\":\"Male\",\"date_of_birth\":\"1990-01-15\",\"email\":\"john@example.com\",\"country\":\"United States\",\"linkedin_url\":\"https://linkedin.com/in/johndoe\",\"education\":[\"BS Computer Science\"],\"employment_history\":[],\"achievement\":\"Built SaaS product\",\"personal_statement\":\"Looking for co-founder\",\"social_links\":{},\"professional_background\":\"Engineering\",\"industries_of_interest\":[\"SaaS\"],\"responsibilities_offered\":[\"CTO\"],\"skills_needed\":[\"Marketing\"],\"preferred_languages\":[{\"language_id\":\"en\",\"importance\":\"must_have\"}],\"preferred_country\":\"United States\",\"preferred_country_importance\":\"nice_to_have\",\"expected_commitment\":\"Full-time\",\"preferred_commitment\":\"Full-time\",\"commitment_importance\":\"must_have\",\"venture_stage\":[\"Idea\"],\"preferred_venture_stage\":[\"Idea\"],\"age_enabled\":false}" \
  -F "profile_picture=@/path/to/photo.jpg"
```

## Response

### Success (200 OK)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "profile_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "draft",
  "first_name": "John",
  "last_name": "Doe",
  "gender": "Male",
  "date_of_birth": "1990-01-15",
  "email": "john@example.com",
  "profile_picture_url": "https://your-project.supabase.co/storage/v1/object/public/Yuba Profile/profiles/user-id/uuid.jpg",
  "country": "United States",
  "linkedin_url": "https://linkedin.com/in/johndoe",
  "created_at": "2025-01-15T10:30:00.000Z",
  ...
}
```

**Note:** The `profile_picture_url` field contains the Supabase Storage URL where the image is stored in the "Yuba Profile" bucket.

### Error Responses

#### 400 Bad Request - Invalid JSON

```json
{
  "detail": "Invalid JSON data: Expecting value: line 1 column 1 (char 0)"
}
```

#### 400 Bad Request - Invalid File Type

```json
{
  "detail": "Invalid file type. Allowed types: .jpg, .jpeg, .png, .gif, .webp, .bmp"
}
```

#### 400 Bad Request - File Too Large

```json
{
  "detail": "File size exceeds 5MB limit"
}
```

#### 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

## Important Notes

1. **Profile Picture is Optional:** You can save a draft without a profile picture. Just omit the `profile_picture` field from the form data.

2. **JSON String Format:** The `data` parameter must be a valid JSON string. Use `JSON.stringify()` to convert your object.

3. **File Replacement:** If you upload a new profile picture, the old one is automatically deleted from storage.

4. **URL Storage:** The actual image is uploaded to Supabase Storage, and only the URL is saved in the database.

5. **No Nested FormData:** Don't nest objects in form data. All profile data should be in the JSON string passed to the `data` parameter.

## Common Mistakes

❌ **Wrong - Sending JSON directly:**
```javascript
// This won't work
fetch("/profiles/me/save-draft", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(profileData)
});
```

✅ **Correct - Using FormData:**
```javascript
const formData = new FormData();
formData.append("data", JSON.stringify(profileData));
formData.append("profile_picture", file);

fetch("/profiles/me/save-draft", {
  method: "POST",
  body: formData  // No Content-Type header needed
});
```

❌ **Wrong - Adding file as separate fields:**
```javascript
// This won't work
formData.append("first_name", "John");
formData.append("last_name", "Doe");
```

✅ **Correct - All data in JSON string:**
```javascript
formData.append("data", JSON.stringify({
  first_name: "John",
  last_name: "Doe",
  // ... all other fields
}));
```
