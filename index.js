// Import required modules
const express = require('express');
const mongoose = require('mongoose');
const bodyParser = require('body-parser');
const cors = require('cors');
const dotenv = require('dotenv');
dotenv.config();

// Initialize Express app
const app = express();
const port = 3000;

// Middleware
app.use(cors());
app.use(bodyParser.json());

// MongoDB Connection
const mongoURI = process.env.mongoURI;
if (!mongoURI) {
  console.error('Error: MONGO_URI is not defined in the environment variables.');
  process.exit(1);
}

mongoose.connect(mongoURI, { useNewUrlParser: true, useUnifiedTopology: true })
  .then(() => console.log('Connected to MongoDB'))
  .catch(err => {
    console.error('Error connecting to MongoDB:', err);
    process.exit(1);
  });

// Define schemas and models
const testSchema = new mongoose.Schema({
  testData: { type: Number, required: true },
  testId: { type: String, required: true },
  timestamp: { type: Date, default: Date.now },
});

const constantSchema = new mongoose.Schema({
  coeff: { type: Number, required: true },
  intercept: { type: Number, required: true },
  Iinitial: { type: Number, required: true },
});

const Test = mongoose.model('Test', testSchema);
const Constant = mongoose.model('Constant', constantSchema);

// API endpoint to add test data
app.post('/addTest', async (req, res) => {
  const { testData, testId } = req.body;

  // Input validation
  if (typeof testData !== 'number' || !testId) {
    return res.status(400).json({ error: 'Invalid input. testData must be a number and testId must be a string.' });
  }

  try {
    // Fetch coefficients and intercept from the constants collection
    const constant = await Constant.findById("6789b2e80833e6f80d72e79b");
    if (!constant) {
      return res.status(404).json({ error: 'Constants not found.' });
    }

    const { coeff, intercept ,Iinitial} = constant;

    // Calculate result
   
    const abs=Math.log10(Iinitial/testData);
    const result = ((coeff / 10000) * abs) + (intercept / 10000);

    // Save to MongoDB
    const newTest = new Test({ testData, testId });
    await newTest.save();

    // Respond with the result and saved data
    res.status(201).json({ result, savedData: newTest });
  } catch (error) {
    console.error('Error processing request:', error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// Default route
app.get('/', (req, res) => {
  res.status(200).json({ message: 'Welcome to the Test API!' });
});

// Start server
app.listen(port, '0.0.0.0', () => {
  console.log(`Server running on http://localhost:${port}`);
});
