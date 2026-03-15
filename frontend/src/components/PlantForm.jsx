import { useState, useEffect } from "react";

/**
 * PlantForm component for creating or editing plants
 * @param {Object} plant - Existing plant data for edit mode (null for create mode)
 * @param {Function} onSubmit - Callback function when form is submitted
 * @param {Function} onCancel - Callback function when form is cancelled
 */
function PlantForm({ plant = null, onSubmit, onCancel }) {
  const [formData, setFormData] = useState({
    plant_id: "",
    name: "",
    location: "",
  });
  const [errors, setErrors] = useState({});
  const isEditMode = plant !== null;

  useEffect(() => {
    if (plant) {
      setFormData({
        plant_id: plant.plant_id || "",
        name: plant.name || "",
        location: plant.location || "",
      });
    }
  }, [plant]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    // Clear error for this field
    if (errors[name]) {
      setErrors((prev) => ({
        ...prev,
        [name]: null,
      }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    if (!formData.plant_id.trim()) {
      newErrors.plant_id = "Plant ID is required";
    }
    if (formData.plant_id.length > 64) {
      newErrors.plant_id = "Plant ID cannot exceed 64 characters";
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validateForm()) {
      onSubmit(formData);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="plant-form">
      <div className="form-group">
        <label htmlFor="plant_id">
          Plant ID <span className="required">*</span>
        </label>
        <input
          type="text"
          id="plant_id"
          name="plant_id"
          value={formData.plant_id}
          onChange={handleChange}
          disabled={isEditMode}
          placeholder="e.g., plant_01"
          className={errors.plant_id ? "error" : ""}
        />
        {errors.plant_id && (
          <span className="error-message">{errors.plant_id}</span>
        )}
        {isEditMode && (
          <span className="help-text">Plant ID cannot be changed</span>
        )}
      </div>

      <div className="form-group">
        <label htmlFor="name">Name</label>
        <input
          type="text"
          id="name"
          name="name"
          value={formData.name}
          onChange={handleChange}
          placeholder="e.g., Tomato Plant"
        />
      </div>

      <div className="form-group">
        <label htmlFor="location">Location</label>
        <input
          type="text"
          id="location"
          name="location"
          value={formData.location}
          onChange={handleChange}
          placeholder="e.g., Kitchen Window"
        />
      </div>

      <div className="form-actions">
        <button type="submit" className="btn btn-primary">
          {isEditMode ? "Update Plant" : "Create Plant"}
        </button>
        <button type="button" onClick={onCancel} className="btn btn-secondary">
          Cancel
        </button>
      </div>
    </form>
  );
}

export default PlantForm;
