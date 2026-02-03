/**
 * E2E tests for complete user onboarding journeys
 * 
 * These tests cover end-to-end user flows:
 * - Team leader invitation → sign up → create team → invite members
 * - Team member invitation → sign in → join team
 * - Organization member invitation → sign up → join → route to correct page
 * 
 * Note: These tests are designed for Playwright or Cypress
 * Run with: npx playwright test or npx cypress run
 */

import { test, expect, Page } from '@playwright/test';

// Test configuration
const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_URL = process.env.API_URL || 'http://localhost:8000';

// Test data
const testData = {
  organization: {
    name: 'Test Organization',
    id: 'test-org-123',
  },
  teamLeader: {
    email: 'team.leader@test.com',
    password: 'TestPassword123!',
    name: 'Team Leader',
  },
  teamMember: {
    email: 'team.member@test.com',
    password: 'TestPassword123!',
    name: 'Team Member',
  },
  orgMember: {
    email: 'org.member@test.com',
    password: 'TestPassword123!',
    name: 'Org Member',
  },
  team: {
    name: 'Engineering Team',
    description: 'Software development team',
    industry: 'Technology',
    size: 'small',
    country: 'Nigeria',
  },
};

// Helper functions
async function signUp(page: Page, email: string, password: string, name: string) {
  await page.goto(`${BASE_URL}/signup`);
  await page.fill('input[name="email"]', email);
  await page.fill('input[name="password"]', password);
  await page.fill('input[name="name"]', name);
  await page.click('button[type="submit"]');
  
  // Wait for redirect after successful signup
  await page.waitForURL(/\/admin|\/team/, { timeout: 10000 });
}

async function signIn(page: Page, email: string, password: string) {
  await page.goto(`${BASE_URL}/signin`);
  await page.fill('input[name="email"]', email);
  await page.fill('input[name="password"]', password);
  await page.click('button[type="submit"]');
  
  // Wait for redirect after successful signin
  await page.waitForURL(/\/admin|\/team/, { timeout: 10000 });
}

async function createTeam(page: Page, teamData: typeof testData.team) {
  // Fill team creation form
  await page.fill('input[name="name"]', teamData.name);
  await page.fill('textarea[name="description"]', teamData.description);
  
  // Select industry
  await page.click('button[id="industry"]');
  await page.click(`text=${teamData.industry}`);
  
  // Select size
  await page.click('button[id="size"]');
  await page.click(`text=${teamData.size}`);
  
  // Select country
  await page.click('button[id="country"]');
  await page.click(`text=${teamData.country}`);
  
  // Submit form
  await page.click('button[type="submit"]:has-text("Create Team")');
  
  // Wait for success and redirect
  await expect(page.locator('text=Team created successfully')).toBeVisible({ timeout: 5000 });
  await page.waitForURL(/\/admin\/team-leader-dashboard/, { timeout: 10000 });
}

test.describe('E2E: Team Leader Journey', () => {
  test('Complete flow: Team leader invitation → sign up → create team → invite members', async ({ page }) => {
    // Step 1: Simulate receiving team leader invitation
    // In real scenario, this would be sent via email
    const inviteToken = 'test-team-leader-invite-token';
    const inviteUrl = `${BASE_URL}/org-invite/${inviteToken}?org_id=${testData.organization.id}`;
    
    // Step 2: Click invitation link (not authenticated)
    await page.goto(inviteUrl);
    
    // Should redirect to sign-in with stored token
    await page.waitForURL(/\/signin/, { timeout: 5000 });
    
    // Verify token is stored in sessionStorage
    const storedToken = await page.evaluate(() => {
      return sessionStorage.getItem('invitation_token');
    });
    expect(storedToken).toBeTruthy();
    
    // Step 3: Sign up as new user
    await page.fill('input[name="email"]', testData.teamLeader.email);
    await page.fill('input[name="password"]', testData.teamLeader.password);
    await page.fill('input[name="name"]', testData.teamLeader.name);
    await page.click('button[type="submit"]');
    
    // Step 4: Should redirect to team leader onboarding
    await page.waitForURL(/\/admin\/team-leader-onboarding/, { timeout: 10000 });
    
    // Verify page content
    await expect(page.locator('h1:has-text("Create Your Team")')).toBeVisible();
    
    // Step 5: Create team
    await createTeam(page, testData.team);
    
    // Step 6: Verify redirect to team leader dashboard
    await expect(page).toHaveURL(/\/admin\/team-leader-dashboard/);
    
    // Verify team metrics are displayed
    await expect(page.locator(`text=${testData.team.name}`)).toBeVisible();
    await expect(page.locator('text=Credit Pool')).toBeVisible();
    await expect(page.locator('text=Team Members')).toBeVisible();
    
    // Step 7: Invite team members
    const memberEmail = testData.teamMember.email;
    await page.fill('input[placeholder*="email"]', memberEmail);
    await page.click('button:has-text("Send Invites")');
    
    // Verify success message
    await expect(page.locator('text=Invitations sent')).toBeVisible({ timeout: 5000 });
    
    // Step 8: Verify invitation appears in pending list (if implemented)
    // await expect(page.locator(`text=${memberEmail}`)).toBeVisible();
  });

  test('Should redirect to dashboard if team already exists', async ({ page, context }) => {
    // Sign in as existing team leader
    await signIn(page, testData.teamLeader.email, testData.teamLeader.password);
    
    // Try to access team leader onboarding
    await page.goto(`${BASE_URL}/admin/team-leader-onboarding`);
    
    // Should redirect to dashboard
    await page.waitForURL(/\/admin\/team-leader-dashboard/, { timeout: 5000 });
    
    // Verify toast message
    await expect(page.locator('text=You already have a team')).toBeVisible({ timeout: 3000 });
  });

  test('Should handle validation errors during team creation', async ({ page }) => {
    // Navigate to team leader onboarding (assume authenticated)
    await signIn(page, testData.teamLeader.email, testData.teamLeader.password);
    await page.goto(`${BASE_URL}/admin/team-leader-onboarding`);
    
    // Try to submit without filling required fields
    await page.click('button[type="submit"]:has-text("Create Team")');
    
    // Verify validation errors are displayed
    await expect(page.locator('text=Team name must be at least 2 characters')).toBeVisible();
    await expect(page.locator('text=Please select an industry')).toBeVisible();
    await expect(page.locator('text=Please select a country')).toBeVisible();
  });
});

test.describe('E2E: Team Member Journey', () => {
  test('Complete flow: Team member invitation → sign in → join team', async ({ page }) => {
    // Step 1: Simulate receiving team member invitation
    const inviteToken = 'test-team-member-invite-token';
    const inviteUrl = `${BASE_URL}/team-invite/${inviteToken}`;
    
    // Step 2: Click invitation link (not authenticated)
    await page.goto(inviteUrl);
    
    // Should redirect to sign-in
    await page.waitForURL(/\/signin/, { timeout: 5000 });
    
    // Verify token is stored
    const storedToken = await page.evaluate(() => {
      return sessionStorage.getItem('invitation_token');
    });
    expect(storedToken).toBeTruthy();
    
    // Step 3: Sign in as existing user
    await page.fill('input[name="email"]', testData.teamMember.email);
    await page.fill('input[name="password"]', testData.teamMember.password);
    await page.click('button[type="submit"]');
    
    // Step 4: Should redirect back to team invite page
    await page.waitForURL(/\/team-invite/, { timeout: 10000 });
    
    // Verify team information is displayed
    await expect(page.locator('h1:has-text("Team Invitation")')).toBeVisible();
    await expect(page.locator(`text=${testData.team.name}`)).toBeVisible();
    
    // Step 5: Join team
    await page.click('button:has-text("Join Team")');
    
    // Verify success message
    await expect(page.locator('text=Successfully joined the team')).toBeVisible({ timeout: 5000 });
    
    // Step 6: Verify redirect to team workspace
    await page.waitForURL(/\/team\/dashboard/, { timeout: 10000 });
    
    // Verify team workspace content
    await expect(page.locator(`text=${testData.team.name}`)).toBeVisible();
  });

  test('Should handle expired invitation token', async ({ page }) => {
    // Use an expired token
    const expiredToken = 'expired-team-invite-token';
    const inviteUrl = `${BASE_URL}/team-invite/${expiredToken}`;
    
    // Sign in first
    await signIn(page, testData.teamMember.email, testData.teamMember.password);
    
    // Navigate to expired invitation
    await page.goto(inviteUrl);
    
    // Should show error message
    await expect(page.locator('text=Invitation Error')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=invitation link has expired')).toBeVisible();
    
    // Verify helpful information is displayed
    await expect(page.locator('text=What to do next')).toBeVisible();
  });

  test('Should handle invalid invitation token', async ({ page }) => {
    // Use an invalid token
    const invalidToken = 'invalid-token-123';
    const inviteUrl = `${BASE_URL}/team-invite/${invalidToken}`;
    
    // Sign in first
    await signIn(page, testData.teamMember.email, testData.teamMember.password);
    
    // Navigate to invalid invitation
    await page.goto(inviteUrl);
    
    // Should show error message
    await expect(page.locator('text=Invitation Error')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=invalid')).toBeVisible();
  });

  test('Should handle already member scenario', async ({ page }) => {
    // Assume user is already a member
    const inviteToken = 'test-team-member-invite-token';
    const inviteUrl = `${BASE_URL}/team-invite/${inviteToken}`;
    
    // Sign in
    await signIn(page, testData.teamMember.email, testData.teamMember.password);
    
    // Navigate to invitation
    await page.goto(inviteUrl);
    
    // Try to join
    await page.click('button:has-text("Join Team")');
    
    // Should show info message and redirect
    await expect(page.locator('text=already a member')).toBeVisible({ timeout: 5000 });
    await page.waitForURL(/\/team\/dashboard/, { timeout: 10000 });
  });
});

test.describe('E2E: Organization Member Journey', () => {
  test('Complete flow: Org member invitation → sign up → join → route to dashboard', async ({ page }) => {
    // Step 1: Simulate receiving organization member invitation
    const inviteToken = 'test-org-member-invite-token';
    const inviteUrl = `${BASE_URL}/org-invite/${inviteToken}?org_id=${testData.organization.id}`;
    
    // Step 2: Click invitation link (not authenticated)
    await page.goto(inviteUrl);
    
    // Should redirect to sign-in
    await page.waitForURL(/\/signin/, { timeout: 5000 });
    
    // Step 3: Sign up as new user
    await page.fill('input[name="email"]', testData.orgMember.email);
    await page.fill('input[name="password"]', testData.orgMember.password);
    await page.fill('input[name="name"]', testData.orgMember.name);
    await page.click('button[type="submit"]');
    
    // Step 4: Should join organization and redirect to dashboard
    await page.waitForURL(/\/admin\/organizations/, { timeout: 10000 });
    
    // Verify success message
    await expect(page.locator('text=Successfully joined organization')).toBeVisible({ timeout: 5000 });
    
    // Verify organization dashboard content
    await expect(page.locator(`text=${testData.organization.name}`)).toBeVisible();
  });

  test('Team leader should be routed to team creation', async ({ page }) => {
    // Simulate team leader invitation
    const inviteToken = 'test-team-leader-org-invite-token';
    const inviteUrl = `${BASE_URL}/org-invite/${inviteToken}?org_id=${testData.organization.id}`;
    
    // Sign up as team leader
    await page.goto(inviteUrl);
    await page.waitForURL(/\/signin/, { timeout: 5000 });
    
    await page.fill('input[name="email"]', 'new.team.leader@test.com');
    await page.fill('input[name="password"]', 'TestPassword123!');
    await page.fill('input[name="name"]', 'New Team Leader');
    await page.click('button[type="submit"]');
    
    // Should redirect to team leader onboarding
    await page.waitForURL(/\/admin\/team-leader-onboarding/, { timeout: 10000 });
    
    // Verify page content
    await expect(page.locator('h1:has-text("Create Your Team")')).toBeVisible();
  });

  test('Should handle expired organization invitation', async ({ page }) => {
    const expiredToken = 'expired-org-invite-token';
    const inviteUrl = `${BASE_URL}/org-invite/${expiredToken}?org_id=${testData.organization.id}`;
    
    // Sign in first
    await signIn(page, testData.orgMember.email, testData.orgMember.password);
    
    // Navigate to expired invitation
    await page.goto(inviteUrl);
    
    // Should show error
    await expect(page.locator('text=Invitation Error')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=invitation link has expired')).toBeVisible();
  });

  test('Should handle missing organization ID', async ({ page }) => {
    const inviteToken = 'test-org-invite-token';
    const inviteUrl = `${BASE_URL}/org-invite/${inviteToken}`; // No org_id parameter
    
    // Sign in first
    await signIn(page, testData.orgMember.email, testData.orgMember.password);
    
    // Navigate to invitation without org_id
    await page.goto(inviteUrl);
    
    // Should show error
    await expect(page.locator('text=Organization ID not found')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('E2E: Cross-Flow Scenarios', () => {
  test('Token should persist across page refreshes', async ({ page }) => {
    const inviteToken = 'test-persistent-token';
    const inviteUrl = `${BASE_URL}/team-invite/${inviteToken}`;
    
    // Navigate to invitation (not authenticated)
    await page.goto(inviteUrl);
    await page.waitForURL(/\/signin/, { timeout: 5000 });
    
    // Verify token is stored
    let storedToken = await page.evaluate(() => {
      return sessionStorage.getItem('invitation_token');
    });
    expect(storedToken).toBeTruthy();
    
    // Refresh page
    await page.reload();
    
    // Token should still be there
    storedToken = await page.evaluate(() => {
      return sessionStorage.getItem('invitation_token');
    });
    expect(storedToken).toBeTruthy();
  });

  test('Token should be cleared after successful onboarding', async ({ page }) => {
    // Complete a full onboarding flow
    const inviteToken = 'test-clearable-token';
    const inviteUrl = `${BASE_URL}/team-invite/${inviteToken}`;
    
    await page.goto(inviteUrl);
    await page.waitForURL(/\/signin/, { timeout: 5000 });
    
    // Sign in
    await signIn(page, testData.teamMember.email, testData.teamMember.password);
    
    // Join team
    await page.click('button:has-text("Join Team")');
    await page.waitForURL(/\/team\/dashboard/, { timeout: 10000 });
    
    // Verify token is cleared
    const storedToken = await page.evaluate(() => {
      return sessionStorage.getItem('invitation_token');
    });
    expect(storedToken).toBeNull();
  });

  test('Expired token should be cleared automatically', async ({ page }) => {
    // Create an expired token
    const expiredTimestamp = Date.now() - (49 * 60 * 60 * 1000); // 49 hours ago
    const expiredToken = {
      token: 'expired-token',
      type: 'team_member',
      timestamp: expiredTimestamp,
    };
    
    // Manually set expired token in sessionStorage
    await page.goto(`${BASE_URL}/signin`);
    await page.evaluate((token) => {
      sessionStorage.setItem('invitation_token', JSON.stringify(token));
    }, expiredToken);
    
    // Sign in
    await signIn(page, testData.teamMember.email, testData.teamMember.password);
    
    // Token should be cleared due to expiry
    const storedToken = await page.evaluate(() => {
      return sessionStorage.getItem('invitation_token');
    });
    expect(storedToken).toBeNull();
  });
});

test.describe('E2E: Error Recovery', () => {
  test('Should allow retry after network error', async ({ page }) => {
    // Simulate network error during team creation
    await signIn(page, testData.teamLeader.email, testData.teamLeader.password);
    await page.goto(`${BASE_URL}/admin/team-leader-onboarding`);
    
    // Intercept API call and fail it
    await page.route('**/teams/create', (route) => {
      route.abort('failed');
    });
    
    // Fill form and submit
    await createTeam(page, testData.team);
    
    // Should show error message
    await expect(page.locator('text=Network error')).toBeVisible({ timeout: 5000 });
    
    // Remove intercept
    await page.unroute('**/teams/create');
    
    // Retry should work
    await page.click('button[type="submit"]:has-text("Create Team")');
    await expect(page.locator('text=Team created successfully')).toBeVisible({ timeout: 5000 });
  });

  test('Should provide helpful error messages', async ({ page }) => {
    // Test various error scenarios
    const scenarios = [
      {
        url: '/team-invite/invalid-token',
        expectedError: 'invalid',
      },
      {
        url: '/team-invite/expired-token',
        expectedError: 'expired',
      },
      {
        url: '/org-invite/invalid-token',
        expectedError: 'invalid',
      },
    ];
    
    for (const scenario of scenarios) {
      await signIn(page, testData.teamMember.email, testData.teamMember.password);
      await page.goto(`${BASE_URL}${scenario.url}`);
      
      await expect(page.locator(`text=${scenario.expectedError}`)).toBeVisible({ timeout: 5000 });
      
      // Verify help text is present
      await expect(page.locator('text=Need help')).toBeVisible();
      await expect(page.locator('a[href*="support"]')).toBeVisible();
    }
  });
});
