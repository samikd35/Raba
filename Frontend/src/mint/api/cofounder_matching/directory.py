from fastapi import APIRouter, Depends, HTTPException

from ..auth_v2.utils import get_current_user
from .directory_service import DirectoryService
from .models import DirectoryFilters, DirectorySearchResponse, DirectoryUser

router = APIRouter(prefix="/profiles", tags=["profiles.directory"])


@router.post("/directory/search", response_model=DirectorySearchResponse)
async def search_directory(
    filters: DirectoryFilters,
    current_user: dict = Depends(get_current_user),
):
    """
    Get the directory of approved users (visible only to approved profiles).
    Admins and super_admins can access without an approved profile.
    Filters:
    - countries (list[str]) -> lowercase country names
    - languages (list[str])
    - age_min / age_max
    - preferred_commitment
    - preferred_venture_stage
    """
    user_id = current_user.get("user_id")
    user_role = current_user.get("roles", [])[0] if current_user.get("roles") else None
    service = DirectoryService()

    # Check if user is admin or super_admin
    is_admin = user_role in ["admin", "super_admin"]

    # Gate: only approved users or admins can view directory
    if not is_admin and not await service.user_is_approved(user_id):
        raise HTTPException(
            status_code=403, detail="Directory visible only to approved users"
        )

    # Calculate offset from page number
    offset = (filters.page - 1) * filters.limit

    # Pass the calculated offset to the service
    filters_dict = filters.dict()
    filters_dict["offset"] = offset

    total, items = await service.search_directory(filters_dict, user_id)

    # Calculate total pages
    total_pages = (total + filters.limit - 1) // filters.limit if filters.limit > 0 else 1

    return DirectorySearchResponse(
        total=total,
        limit=filters.limit,
        offset=offset,
        page=filters.page,
        total_pages=total_pages,
        items=[
            DirectoryUser(
                user_id=i["user_id"],
                profile_id=i["profile_id"],
                version_id=i["version_id"],
                full_name=i.get("full_name"),
                country=i.get("preferred_country"),
                date_of_birth=i.get("date_of_birth"),
                profile_picture_url=i.get("profile_picture_url"),
                professional_background=i.get("professional_background"),
                can_message=i.get("can_message", False),
            )
            for i in items
        ],
    )


@router.get("/directory/versions/{version_id}")
async def get_version_details(
    version_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get details of a specific profile version (no ownership check required).
    Only approved users or admins can access this endpoint.
    """
    user_id = current_user.get("user_id")
    user_role = current_user.get("roles", [])[0] if current_user.get("roles") else None
    service = DirectoryService()

    # Check if user is admin or super_admin
    is_admin = user_role in ["admin", "super_admin"]

    # Gate: only approved users or admins can view version details
    if not is_admin and not await service.user_is_approved(user_id):
        raise HTTPException(
            status_code=403, detail="Version details visible only to approved users"
        )

    version = await service.get_version_details(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    return version
