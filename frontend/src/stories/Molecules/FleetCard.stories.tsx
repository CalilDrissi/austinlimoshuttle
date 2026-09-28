import type { Meta, StoryObj } from "@storybook/react";
import type { Vehicle } from "@/types";

const MOCK_VEHICLE: Vehicle = {
  id: "1",
  slug: "business-sedan",
  name: "Business Sedan",
  class: "Business Class",
  image: "/assets/imgs/page/homepage1/banner.png",
  passengers: 4,
  luggage: 2,
  price: 125.25,
  facilities: ["WiFi", "Water", "Newspaper"],
};

function FleetCard({ vehicle }: { vehicle: Vehicle }) {
  return (
    <div className="item-vehicle" style={{ border: "1px solid #e5e7eb", borderRadius: 12, padding: 24, maxWidth: 700 }}>
      <div className="vehicle-left">
        <div className="vehicle-facilities">
          {vehicle.facilities.map((f) => (
            <span key={f} className="text-14 color-grey mr-10">{f}</span>
          ))}
        </div>
      </div>
      <div className="vehicle-right">
        <h5 className="text-20-medium color-text mb-5">{vehicle.name}</h5>
        <p className="text-14 color-grey mb-10">{vehicle.class}</p>
        <div className="d-flex align-items-center mb-10">
          <span className="text-14 color-grey mr-20">Passengers {vehicle.passengers}</span>
          <span className="text-14 color-grey">Luggage {vehicle.luggage}</span>
        </div>
        <span className="heading-24-medium color-primary">${vehicle.price.toFixed(2)}</span>
        <div className="mt-15">
          <button className="btn btn-primary hover-up">Select</button>
        </div>
      </div>
    </div>
  );
}

const meta: Meta<typeof FleetCard> = {
  title: "Molecules/FleetCard",
  component: FleetCard,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
};
export default meta;
type Story = StoryObj<typeof FleetCard>;

export const Default: Story = { args: { vehicle: MOCK_VEHICLE } };
export const VIP: Story = {
  args: {
    vehicle: {
      ...MOCK_VEHICLE,
      id: "4",
      name: "VIP Limousine",
      class: "VIP Class",
      price: 546.23,
      passengers: 8,
      facilities: ["WiFi", "Champagne", "TV", "Mini Bar"],
    },
  },
};
