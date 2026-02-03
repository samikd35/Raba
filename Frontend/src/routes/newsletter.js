const express = require('express');
const fs = require('fs').promises;
const path = require('path');
const router = express.Router();

const SUBSCRIBERS_FILE = path.join(__dirname, '../../data/subscribers.json');

// Ensure data directory exists
const ensureDataDir = async () => {
  const dataDir = path.dirname(SUBSCRIBERS_FILE);
  try {
    await fs.access(dataDir);
  } catch {
    await fs.mkdir(dataDir, { recursive: true });
  }
};

// Get all subscribers
const getSubscribers = async () => {
  try {
    await ensureDataDir();
    const data = await fs.readFile(SUBSCRIBERS_FILE, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    if (error.code === 'ENOENT') {
      return [];
    }
    throw error;
  }
};

// Save subscribers
const saveSubscribers = async (subscribers) => {
  await ensureDataDir();
  await fs.writeFile(SUBSCRIBERS_FILE, JSON.stringify(subscribers, null, 2));
};

// POST /api/newsletter/subscribe
router.post('/subscribe', async (req, res) => {
  try {
    const { email } = req.body;
    
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return res.status(400).json({ error: 'Invalid email address' });
    }

    const processedEmail = email.trim().toLowerCase();
    const subscribers = await getSubscribers();
    
    // Check for duplicates
    if (subscribers.some(sub => sub.email === processedEmail)) {
      return res.status(409).json({ error: 'Already subscribed' });
    }
    
    // Add new subscriber
    subscribers.push({
      email: processedEmail,
      subscribedAt: new Date().toISOString()
    });
    
    await saveSubscribers(subscribers);
    
    res.status(201).json({ message: 'Successfully subscribed!' });
  } catch (error) {
    console.error('Newsletter subscription error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router;
